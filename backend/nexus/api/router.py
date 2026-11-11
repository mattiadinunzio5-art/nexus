from fastapi import APIRouter

from .routes import (
    activity,
    agents,
    auth,
    connectors,
    credentials,
    finance,
    dashboard,
    discovery,
    documents,
    graph,
    history,
    lab,
    lessons,
    modules,
    notifications,
    policy,
    projects,
    research,
    search,
    sources,
    studio,
    system,
)

api_router = APIRouter(prefix="/api")
for r in (system, modules, dashboard, projects, activity, notifications, policy, connectors, search, documents, sources, research, history, graph, finance, credentials, agents, lab, lessons, studio, discovery, auth):
    api_router.include_router(r.router)
