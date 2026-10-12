"""Reading an item through its public link: no account, read only.

Nothing here is written for the link. The routes are the workspace's own GET routes,
picked one by one (`READABLE`) and mounted under `/shared/{token}`, so a page reads the
same shapes as in the app. Three things keep them from showing more than the link covers:

- the request's session is confined to the workspace of the link (`scope_to_share`);
- every id in the path must be in what the link reaches (`share_scope`), otherwise it
  is a 404, as if the row did not exist;
- what the app shows about people, tags and the files on the server is blanked
  (`scrub`).
"""

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from fastapi.routing import APIRoute
from sqlmodel import select

import config
from api import analyses, batches, experiment_executions, experiments, studies
from db import SessionDep
from schemas.shares import SharedRoot
from share_scope import ROOT_TABLES, Scope, scope_of
from tables import Share
from workspace_scope import scope_session

# The GET routes of the workspace that a link opens, with how their answer is shown.
# Everything else (lists, writes, notes, tags, datasets, prompts, models) stays out.
READABLE = {
    "/studies/{study_id}",
    "/batches/{batch_id}",
    "/experiments/{exp_id}",
    "/experiments/{experiment_id}/executions",
    "/executions/{execution_id}",
    "/analyses/metrics",
    "/analyses/{analysis_id}",
    # What the dataset rows and the agents' outputs are made of: shown as they are
    "/executions/{execution_id}/results",
    "/executions/{execution_id}/analysis-fields",
    "/executions/{execution_id}/rows/{row_index}",
    "/analyses/{analysis_id}/results",
}
DATA = {
    "/executions/{execution_id}/results",
    "/executions/{execution_id}/analysis-fields",
    "/executions/{execution_id}/rows/{row_index}",
    "/analyses/{analysis_id}/results",
}

# The id in a path, and what it is the id of
PATH_IDS = {
    "study_id": "study",
    "batch_id": "batch",
    "exp_id": "experiment",
    "experiment_id": "experiment",
    "analysis_id": "analysis",
    "execution_id": "execution",
}
# Path parameters that point to nothing
NOT_IDS = {"token", "row_index"}
# What a token and an id in a path look like (`api/shares.py` makes tokens of URL-safe characters)
TOKEN_FORMAT = re.compile(r"[A-Za-z0-9_-]{1,64}")
ID_FORMAT = re.compile(r"[0-9]{1,18}")

# What the app shows that a link must not: the people, the tags, the files of the server
# (`results_file_path` too, see `scrub`)
BLANKED: dict[str, object] = {
    "author": None,
    "added_by": None,
    "tags": [],
    "file_path": None,
    # The experiment a batch came from is not part of the batch: neither is its name
    "base_experiment_id": None,
    "base_experiment_name": None,
}


# What the results of an analysis show of the experiments it compares, which the link does not reach
# (the labels of the runs are the analysis's own words, and stay)
RUN_BLANKED: dict[str, object] = {
    "experiment_id": None,
    "experiment_name": None,
}


def scrub(value: object, scope: Scope, blanked: dict[str, object] = BLANKED) -> object:
    """The answer of a route with the `blanked` fields emptied, wherever they are in it."""
    if isinstance(value, list):
        return [scrub(item, scope, blanked) for item in value]
    if not isinstance(value, dict):
        return value
    # The name of the batch an experiment is in, unless the link reaches that batch
    hide_batch = "batch_id" in value and value["batch_id"] not in scope.batches
    scrubbed = {}
    for key, item in value.items():
        if key in blanked:
            scrubbed[key] = blanked[key]
        elif key == "batch_name" and hide_batch:
            scrubbed[key] = None
        elif key == "results_file_path":
            # Whether the execution has a results file is what a page needs, not where it is
            scrubbed[key] = "results.json" if item else None
        elif key == "dataset_snapshot" and isinstance(item, str):
            # A JSON text of the dataset, as it was when the execution started
            try:
                scrubbed[key] = json.dumps(scrub(json.loads(item), scope, blanked))
            except ValueError:
                scrubbed[key] = item
        else:
            scrubbed[key] = scrub(item, scope, blanked)
    return scrubbed


class ScrubbedRoute(APIRoute):
    """A route whose JSON answer goes through `scrub`."""

    blanked = BLANKED

    def get_route_handler(self) -> Callable:
        handler = super().get_route_handler()

        async def scrubbed(request: Request) -> Response:
            response = await handler(request)
            # The answer of a route with a response model: JSON bytes in a plain Response
            if response.media_type != "application/json" or not hasattr(response, "body"):
                return response
            headers = {
                name: value
                for name, value in response.headers.items()
                if name.lower() not in ("content-length", "content-type")
            }
            # Set by `scope_to_share`, which ran for this request
            access: Access = request.state.share_access
            return JSONResponse(
                scrub(json.loads(response.body), access.scope, self.blanked),
                status_code=response.status_code,
                headers=headers,
            )

        return scrubbed


class RunsScrubbedRoute(ScrubbedRoute):
    """The results of an analysis: its runs without the experiment they come from."""

    blanked = RUN_BLANKED


class DownloadRoute(APIRoute):
    """The download of a results file, named after its execution, not after its experiment."""

    def get_route_handler(self) -> Callable:
        handler = super().get_route_handler()

        async def named(request: Request) -> Response:
            response = await handler(request)
            execution_id = request.path_params["execution_id"]
            response.headers["content-disposition"] = (
                f'attachment; filename="execution_{execution_id}_results.json"'
            )
            return response

        return named


@dataclass(frozen=True)
class Access:
    share: Share
    scope: Scope


def scope_to_share(token: str, request: Request, session: SessionDep) -> Access:
    """Router-level dependency: open the link, confine the session, check the ids."""
    if not config.PUBLIC_SHARING_ENABLED:
        raise HTTPException(status_code=404, detail="This link does not exist")
    # Anything that cannot be a token is refused before the database is asked
    if not TOKEN_FORMAT.fullmatch(token):
        raise HTTPException(status_code=404, detail="This link does not exist")
    # The session is not confined yet: the link is looked up across workspaces
    share = session.exec(select(Share).where(Share.token == token)).first()
    if share is None:
        raise HTTPException(status_code=404, detail="This link does not exist")
    if share.revoked_at is not None:
        raise HTTPException(status_code=410, detail="This link is no longer active")

    scope_session(session, share.workspace_id)
    scope = scope_of(session, share.kind, share.item_id)
    if not scope.root_found:
        raise HTTPException(status_code=404, detail="This link does not exist")

    for name, value in request.path_params.items():
        if name in NOT_IDS:
            continue
        # A path id this does not know is refused: a new route cannot slip through
        kind = PATH_IDS.get(name)
        if kind is None or not ID_FORMAT.fullmatch(str(value)) or int(value) not in scope.ids(kind):
            raise HTTPException(status_code=404, detail="Not found")
    access = Access(share=share, scope=scope)
    request.state.share_access = access
    return access


router = APIRouter(
    prefix="/shared/{token}",
    tags=["shared"],
    dependencies=[Depends(scope_to_share)],
)


@router.get("", response_model=SharedRoot)
def get_root(access: Annotated[Access, Depends(scope_to_share)], session: SessionDep):
    """What the link points to."""
    share = access.share
    item = session.get(ROOT_TABLES[share.kind], share.item_id)
    return SharedRoot(kind=share.kind, item_id=share.item_id, name=item.name)


def _route_class(path: str) -> type[APIRoute] | None:
    if path == "/executions/{execution_id}/results":
        return DownloadRoute
    if path == "/analyses/{analysis_id}/results":
        return RunsScrubbedRoute
    return None if path in DATA else ScrubbedRoute


def _mount_readable_routes() -> None:
    mounted = set()
    for module in (studies, batches, experiments, experiment_executions, analyses):
        for route in module.router.routes:
            if (
                not isinstance(route, APIRoute)
                or route.path not in READABLE
                or route.methods != {"GET"}
            ):
                continue
            router.add_api_route(
                route.path,
                route.endpoint,
                methods=["GET"],
                response_model=route.response_model,
                name=route.name,
                route_class_override=_route_class(route.path),
            )
            mounted.add(route.path)
    if missing := READABLE - mounted:
        raise RuntimeError(f"Readable routes that no longer exist: {sorted(missing)}")


_mount_readable_routes()


async def public_headers(request: Request, call_next):
    """What the pages of a link must say to browsers and crawlers."""
    response = await call_next(request)
    if request.url.path.startswith("/shared/"):
        # Not for search engines; and the link is in the page address, which must not
        # travel in a Referer to the sites it links to. A withdrawn link must stop at once.
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "private, no-cache"
    return response
