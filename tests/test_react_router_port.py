import time
from io import StringIO

from pyinkcli import render
from pyinkcli.component import createElement
from pyinkcli.packages.react_router import (
    DataWithResponseInit,
    ErrorResponseImpl,
    Headers,
    MemoryRouter,
    Navigate,
    Outlet,
    Path,
    Response,
    Route,
    Routes,
    RouterContextProvider,
    Update,
    createRedirectErrorDigest,
    createRoutesFromChildren,
    createRoutesFromElements,
    createRouteErrorResponseDigest,
    compilePath,
    convertRoutesToDataRoutes,
    convertRouteMatchToUiMatch,
    createContext,
    createLocation,
    createPath,
    data,
    decodeRedirectErrorDigest,
    decodeRouteErrorResponseDigest,
    decodePath,
    generatePath,
    getPathContributingMatches,
    getRoutePattern,
    getResolveToMatches,
    href,
    isBrowser,
    isAbsoluteUrl,
    isRouteErrorResponse,
    isUnsupportedLazyRouteFunctionKey,
    isUnsupportedLazyRouteObjectKey,
    joinPaths,
    matchPath,
    matchRoutes,
    matchRoutesImpl,
    mapRouteProperties,
    normalizeHash,
    normalizePathname,
    normalizeSearch,
    parseToInfo,
    prependBasename,
    redirect,
    redirectDocument,
    replace,
    stripBasename,
    throwIfPotentialCSRFAttack,
    hydrationRouteProperties,
    useHref,
    useMatch,
    useNavigationType,
    useOutletContext,
    useParams,
    useResolvedPath,
    useRoutes,
)
from pyinkcli.packages.react_router.router import RouteObject, createMemoryHistory, resolvePath
from pyinkcli.render_to_string import renderToString
from pyinkcli.components.Box import Box
from pyinkcli.components.Text import Text


def _home():
    return Text("Home")


def _about():
    return Text("About")


def _layout():
    return Box(
        Text("Layout"),
        createElement(Outlet),
        flexDirection="column",
    )


def _layout_with_context():
    return Box(
        Text("Layout"),
        createElement(Outlet, context="dashboard"),
        flexDirection="column",
    )


def _user():
    params = useParams()
    return Text(f"User:{params['userId']}")


def _outlet_context_probe():
    return Text(f"Context:{useOutletContext()}")


def _href_probe():
    return Text(useHref("/about"))


def _navigation_type_probe():
    return Text(useNavigationType())


def _match_probe():
    match = useMatch("/users/:userId")
    return Text(f"Match:{match['params']['userId']}" if match else "Match:none")


def _resolved_path_probe():
    path = useResolvedPath("../about")
    return Text(path["pathname"])


def _resolved_path_route_relative_probe():
    path = useResolvedPath("..")
    return Text(f"route:{path['pathname']}")


def _resolved_path_path_relative_probe():
    path = useResolvedPath("..", {"relative": "path"})
    return Text(f"path:{path['pathname']}")


def _object_routes_probe():
    return useRoutes(
        [
            RouteObject(
                id="root",
                path="/",
                element=createElement(_layout),
                children=[
                    RouteObject(
                        id="about",
                        path="about",
                        element=createElement(_about),
                    )
                ],
            )
        ]
    )


class _FakeStdout(StringIO):
    def isatty(self) -> bool:
        return False


class _FakeStdin(StringIO):
    def isatty(self) -> bool:
        return False


def _build_app(*, initial_entries=None):
    return createElement(
        MemoryRouter,
        createElement(
            Routes,
            createElement(Route, path="/", element=createElement(_home)),
            createElement(Route, path="/about", element=createElement(_about)),
        ),
        initialEntries=initial_entries,
    )


def test_create_routes_from_children_builds_route_objects() -> None:
    routes = createRoutesFromChildren(
        createElement(
            Routes,
            createElement(Route, path="/", element=createElement(_home)),
            createElement(Route, path="/about", element=createElement(_about)),
        ).children
    )
    assert [route.path for route in routes] == ["/", "/about"]
    assert routes[0].id == "0"
    assert routes[1].id == "1"


def test_create_routes_from_elements_alias_matches_children_helper() -> None:
    children = createElement(
        Routes,
        createElement(Route, path="/", element=createElement(_home)),
        createElement(Route, path="/about", element=createElement(_about)),
    ).children
    from_children = createRoutesFromChildren(children)
    from_elements = createRoutesFromElements(children)

    assert [route.path for route in from_elements] == [route.path for route in from_children]
    assert [route.id for route in from_elements] == [route.id for route in from_children]


def test_map_route_properties_matches_upstream_component_conversions() -> None:
    route = RouteObject(
        id="route",
        Component=_home,
        HydrateFallback=_about,
        ErrorBoundary=_layout,
    )

    updates = mapRouteProperties(route)
    assert updates["hasErrorBoundary"] is True
    assert updates["Component"] is None
    assert updates["HydrateFallback"] is None
    assert updates["ErrorBoundary"] is None
    assert hydrationRouteProperties == ["HydrateFallback", "hydrateFallbackElement"]
    assert getattr(updates["element"], "type", None) is _home
    assert getattr(updates["hydrateFallbackElement"], "type", None) is _about
    assert getattr(updates["errorElement"], "type", None) is _layout


def test_generate_path_interpolates_params_and_splat() -> None:
    assert generatePath("/users/:userId", {"userId": "42"}) == "/users/42"
    assert generatePath("/files/*", {"*": "docs/readme.md"}) == "/files/docs/readme.md"


def test_history_helpers_cover_location_creation_and_memory_updates() -> None:
    location = createLocation(
        "/current",
        {
            "pathname": "/next",
            "search": "?tab=profile",
            "hash": "#top",
            "state": {"from": "test"},
        },
        key="fixed",
        unstable_mask=Path(pathname="/mask"),
    )
    assert location.pathname == "/next"
    assert location.search == "?tab=profile"
    assert location.hash == "#top"
    assert location.state == {"from": "test"}
    assert location.key == "fixed"
    assert location.unstable_mask == Path(pathname="/mask")

    history = createMemoryHistory({"initialEntries": ["/", "/about"], "initialIndex": 0, "v5Compat": True})
    updates: list[Update] = []
    unlisten = history.listen(lambda update: updates.append(update))
    history.push("/team", {"section": "push"})
    history.replace("/team/settings", {"section": "replace"})
    history.go(-1)
    unlisten()

    assert history.createHref({"pathname": "/team/settings", "search": "?tab=a"}) == "/team/settings?tab=a"
    assert history.encodeLocation("/team/settings?tab=a#top") == {
        "pathname": "/team/settings",
        "search": "?tab=a",
        "hash": "#top",
    }
    assert [update.action.value for update in updates] == ["PUSH", "REPLACE", "POP"]
    assert updates[0].location.pathname == "/team"
    assert updates[1].location.pathname == "/team/settings"
    assert updates[2].location.pathname == "/"


def test_match_path_and_resolve_path_helpers_follow_upstream_behavior() -> None:
    match = matchPath("/users/:userId", "/users/42")
    assert match is not None
    assert match["params"]["userId"] == "42"
    assert resolvePath("../about", "/users/42")["pathname"] == "/users/about"
    assert createPath({"pathname": "/users/42", "search": "?tab=profile", "hash": "#top"}) == "/users/42?tab=profile#top"


def test_router_agnostic_helpers_cover_basename_and_url_utilities() -> None:
    matcher, compiled = compilePath("/users/:userId")
    assert matcher.match("/users/42") is not None
    assert compiled[0]["paramName"] == "userId"
    assert decodePath("/a%20b") == "/a b"
    assert stripBasename("/app/about", "/app") == "/about"
    assert prependBasename(basename="/app", pathname="/about") == "/app/about"
    assert isAbsoluteUrl("https://example.com") is True
    assert joinPaths(["/app/", "/about"]) == "/app/about"
    assert normalizePathname("//app/about/") == "/app/about"
    assert normalizeSearch("tab=profile") == "?tab=profile"
    assert normalizeHash("top") == "#top"
    assert isBrowser is False
    parsed_info = parseToInfo("https://example.com/app/about", "/app")
    assert parsed_info["absoluteURL"] == "https://example.com/app/about"
    assert parsed_info["isExternal"] is False
    assert parsed_info["to"] == "https://example.com/app/about"


def test_data_and_redirect_helpers_follow_upstream_shape() -> None:
    wrapped = data({"ok": True}, 201)
    assert isinstance(wrapped, DataWithResponseInit)
    assert wrapped.type == "DataWithResponseInit"
    assert wrapped.data == {"ok": True}
    assert wrapped.init == {"status": 201}

    response = redirect("/login")
    assert isinstance(response, Response)
    assert response.status == 302
    assert isinstance(response.headers, Headers)
    assert response.headers["Location"] == "/login"

    doc_response = redirectDocument("/logout", {"status": 301})
    assert doc_response.status == 301
    assert doc_response.headers["Location"] == "/logout"
    assert doc_response.headers["X-Remix-Reload-Document"] == "true"

    replace_response = replace("/new-location")
    assert replace_response.headers["Location"] == "/new-location"
    assert replace_response.headers["X-Remix-Replace"] == "true"


def test_href_helper_follows_upstream_param_and_splat_rules() -> None:
    assert href("/:lang?/about", {"lang": "en"}) == "/en/about"
    assert href("/:lang?/about") == "/about"
    assert href("/products/:id", {"id": "abc123"}) == "/products/abc123"
    assert href("/files/*", {"*": "docs/readme.md"}) == "/files/docs/readme.md"

    try:
        href("/products/:id")
    except ValueError as error:
        assert "requires param 'id'" in str(error)
    else:  # pragma: no cover
        raise AssertionError("expected href() to reject missing required params")


def test_csrf_action_helper_matches_origin_and_allowed_origin_rules() -> None:
    throwIfPotentialCSRFAttack(
        Headers(
            {
                "origin": "https://app.example.com",
                "host": "app.example.com",
            }
        ),
        None,
    )

    throwIfPotentialCSRFAttack(
        Headers(
            {
                "origin": "https://api.example.com",
                "x-forwarded-host": "app.example.com",
            }
        ),
        ["*.example.com"],
    )

    try:
        throwIfPotentialCSRFAttack(
            Headers(
                {
                    "origin": "https://evil.example.net",
                    "host": "app.example.com",
                }
            ),
            ["*.example.com"],
        )
    except Exception as error:
        assert "host header does not match `origin` header" in str(error)
    else:  # pragma: no cover
        raise AssertionError("expected origin/host mismatch to fail")

    try:
        throwIfPotentialCSRFAttack(
            Headers({"origin": "not a url"}),
            None,
        )
    except Exception as error:
        assert "`origin` header is not a valid URL" in str(error)
    else:  # pragma: no cover
        raise AssertionError("expected invalid origin header to fail")


def test_error_digest_helpers_round_trip_redirects_and_route_errors() -> None:
    redirect_digest = createRedirectErrorDigest(
        replace("/login", {"status": 307, "statusText": "Temporary Redirect"})
    )
    decoded_redirect = decodeRedirectErrorDigest(redirect_digest)

    assert decoded_redirect == {
        "status": 307,
        "statusText": "Temporary Redirect",
        "location": "/login",
        "reloadDocument": False,
        "replace": True,
    }
    assert decodeRedirectErrorDigest("REACT_ROUTER_ERROR:REDIRECT:oops") is None

    route_digest = createRouteErrorResponseDigest(
        data(
            {"message": "missing"},
            {"status": 404, "statusText": "Not Found"},
        )
    )
    decoded_route = decodeRouteErrorResponseDigest(route_digest)
    assert isinstance(decoded_route, ErrorResponseImpl)
    assert decoded_route.status == 404
    assert decoded_route.statusText == "Not Found"
    assert decoded_route.data == {"message": "missing"}

    response_digest = createRouteErrorResponseDigest(
        Response(status=500, statusText="Boom")
    )
    response_route = decodeRouteErrorResponseDigest(response_digest)
    assert isinstance(response_route, ErrorResponseImpl)
    assert response_route.status == 500
    assert response_route.statusText == "Boom"
    assert response_route.data is None


def test_router_context_provider_uses_context_identity_and_defaults() -> None:
    user_context = createContext(None)
    missing_context = createContext()
    fallback_context = createContext("fallback")
    provider = RouterContextProvider()

    provider.set(user_context, {"id": "u1"})
    assert provider.get(user_context) == {"id": "u1"}
    assert provider.get(fallback_context) == "fallback"

    try:
        provider.get(missing_context)
    except ValueError as error:
        assert "No value found for context" in str(error)
    else:  # pragma: no cover
        raise AssertionError("expected provider.get() without default to fail")


def test_lazy_route_key_guards_match_upstream_sets() -> None:
    assert isUnsupportedLazyRouteObjectKey("path")
    assert isUnsupportedLazyRouteObjectKey("children")
    assert not isUnsupportedLazyRouteObjectKey("loader")
    assert isUnsupportedLazyRouteFunctionKey("middleware")
    assert not isUnsupportedLazyRouteFunctionKey("action")


def test_memory_router_renders_home_entry() -> None:
    output = renderToString(_build_app(initial_entries=["/"]), columns=20, rows=5)
    assert "Home" in output


def test_memory_router_renders_about_entry() -> None:
    output = renderToString(_build_app(initial_entries=["/about"]), columns=20, rows=5)
    assert "About" in output


def test_use_href_applies_basename() -> None:
    app = createElement(
        MemoryRouter,
        createElement(
            Routes,
            createElement(Route, path="/", element=createElement(_href_probe)),
        ),
        basename="/app",
        initialEntries=["/app"],
    )

    output = renderToString(app, columns=30, rows=5)
    assert "/app/about" in output


def test_use_navigation_type_defaults_to_pop() -> None:
    app = createElement(
        MemoryRouter,
        createElement(
            Routes,
            createElement(Route, path="/", element=createElement(_navigation_type_probe)),
        ),
        initialEntries=["/"],
    )

    output = renderToString(app, columns=20, rows=5)
    assert "POP" in output


def test_use_routes_renders_object_route_config() -> None:
    app = createElement(
        MemoryRouter,
        createElement(_object_routes_probe),
        initialEntries=["/about"],
    )

    output = renderToString(app, columns=20, rows=5)
    assert "Layout" in output
    assert "About" in output


def test_match_routes_prefers_earlier_sibling_when_paths_tie() -> None:
    routes = [
        RouteObject(id="first", path="/teams/:teamId", element="first"),
        RouteObject(id="second", path="/teams/:teamId", element="second"),
    ]

    matches = matchRoutes(routes, {"pathname": "/teams/alpha"})
    assert matches is not None
    assert matches[-1].route.id == "first"


def test_convert_routes_to_data_routes_assigns_ids_and_manifest_updates() -> None:
    manifest: dict[str, RouteObject] = {}
    routes = [
        RouteObject(
            id="",
            path="/",
            children=[
                RouteObject(id="", path="about", handle={"section": "about"}),
            ],
        )
    ]

    data_routes = convertRoutesToDataRoutes(
        routes,
        mapRouteProperties,
        manifest=manifest,
    )

    assert data_routes[0].id == "0"
    assert data_routes[0].children[0].id == "0-0"
    assert manifest["0"].id == "0"
    assert manifest["0-0"].hasErrorBoundary is False


def test_convert_routes_to_data_routes_rejects_id_collisions_by_default() -> None:
    routes = [
        RouteObject(id="dup", path="/a"),
        RouteObject(id="dup", path="/b"),
    ]

    try:
        convertRoutesToDataRoutes(routes, lambda route: {})
    except ValueError as error:
        assert 'Found a route id collision on id "dup"' in str(error)
    else:  # pragma: no cover
        raise AssertionError("expected duplicate route ids to fail")


def test_convert_routes_to_data_routes_can_mutate_in_place_when_requested() -> None:
    route = RouteObject(id="", path="/")
    data_routes = convertRoutesToDataRoutes(
        [route],
        lambda current: {"hasErrorBoundary": current.path == "/"},
        allowInPlaceMutations=True,
    )

    assert data_routes[0] is route
    assert route.id == "0"
    assert route.hasErrorBoundary is True


def test_match_routes_impl_supports_partial_matching() -> None:
    routes = [RouteObject(id="users", path="/users")]
    assert matchRoutesImpl(routes, {"pathname": "/users/42"}, "/", True) is not None
    assert matchRoutesImpl(routes, {"pathname": "/users/42"}, "/", False) is None


def test_path_contributing_match_helpers_follow_leaf_rules() -> None:
    root = RouteObject(id="root", path="/")
    layout = RouteObject(id="layout", path=None)
    leaf = RouteObject(id="leaf", path="users/:userId")
    route_matches = [
        type("Match", (), {"route": root, "pathname": "/", "pathnameBase": "/", "params": {}})(),
        type("Match", (), {"route": layout, "pathname": "/", "pathnameBase": "/", "params": {}})(),
        type("Match", (), {"route": leaf, "pathname": "/users/42", "pathnameBase": "/users/42", "params": {"userId": "42"}})(),
    ]
    contributing = getPathContributingMatches(route_matches)
    assert [match.route.id for match in contributing] == ["root", "leaf"]
    assert getResolveToMatches(route_matches) == ["/", "/users/42"]


def test_ui_match_and_route_pattern_helpers_follow_upstream_shape() -> None:
    route = RouteObject(id="leaf", path="users/:userId", handle={"section": "users"})
    match = type(
        "Match",
        (),
        {
            "route": route,
            "pathname": "/users/42",
            "pathnameBase": "/users/42",
            "params": {"userId": "42"},
        },
    )()

    ui_match = convertRouteMatchToUiMatch(match, {"leaf": {"name": "Ada"}})
    assert ui_match.id == "leaf"
    assert ui_match.pathname == "/users/42"
    assert ui_match.params["userId"] == "42"
    assert ui_match.loaderData == {"name": "Ada"}
    assert ui_match.handle == {"section": "users"}
    assert getRoutePattern([match]) == "users/:userId"


def test_is_route_error_response_checks_shape() -> None:
    assert isRouteErrorResponse(
        {
            "status": 404,
            "statusText": "Not Found",
            "internal": False,
            "data": "missing",
        }
    )
    assert not isRouteErrorResponse({"status": "404"})
    assert isRouteErrorResponse(ErrorResponseImpl(500, "Boom", ValueError("bad"), True))


def test_nested_routes_render_outlet_and_params() -> None:
    app = createElement(
        MemoryRouter,
        createElement(
            Routes,
            createElement(
                Route,
                path="/",
                element=createElement(_layout),
                children=createElement(Route, path="users/:userId", element=createElement(_user)),
            ),
        ),
        initialEntries=["/users/42"],
    )

    output = renderToString(app, columns=20, rows=5)
    assert "Layout" in output
    assert "User:42" in output


def test_outlet_context_reaches_child_route() -> None:
    app = createElement(
        MemoryRouter,
        createElement(
            Routes,
            createElement(
                Route,
                path="/",
                element=createElement(_layout_with_context),
                children=createElement(Route, path="child", element=createElement(_outlet_context_probe)),
            ),
        ),
        initialEntries=["/child"],
    )

    output = renderToString(app, columns=30, rows=5)
    assert "Context:dashboard" in output


def test_use_match_matches_current_path() -> None:
    app = createElement(
        MemoryRouter,
        createElement(
            Routes,
            createElement(Route, path="/users/:userId", element=createElement(_match_probe)),
        ),
        initialEntries=["/users/42"],
    )

    output = renderToString(app, columns=20, rows=5)
    assert "Match:42" in output


def test_routes_location_overrides_current_location() -> None:
    app = createElement(
        MemoryRouter,
        createElement(
            Routes,
            createElement(Route, path="/", element=createElement(_home)),
            createElement(Route, path="/about", element=createElement(_about)),
            location="/about",
        ),
        initialEntries=["/"],
    )

    output = renderToString(app, columns=20, rows=5)
    assert "About" in output


def test_use_resolved_path_is_route_relative() -> None:
    app = createElement(
        MemoryRouter,
        createElement(
            Routes,
            createElement(
                Route,
                path="/",
                element=createElement(_layout),
                children=createElement(Route, path="users/:userId", element=createElement(_resolved_path_probe)),
            ),
        ),
        initialEntries=["/users/42"],
    )

    output = renderToString(app, columns=20, rows=5)
    assert "/about" in output


def test_use_resolved_path_supports_path_relative_mode() -> None:
    app = createElement(
        MemoryRouter,
        createElement(
            Routes,
            createElement(
                Route,
                path="/",
                element=createElement(_layout),
                children=createElement(
                    Route,
                    path="users/:userId",
                    element=createElement(Outlet),
                    children=[
                        createElement(Route, path="details", element=createElement(_resolved_path_route_relative_probe)),
                        createElement(Route, path="details-path", element=createElement(_resolved_path_path_relative_probe)),
                    ],
                ),
            ),
        ),
        initialEntries=["/users/42/details"],
    )

    route_relative_output = renderToString(app, columns=20, rows=5)
    assert "route:/" in route_relative_output

    app = createElement(
        MemoryRouter,
        createElement(
            Routes,
            createElement(
                Route,
                path="/",
                element=createElement(_layout),
                children=createElement(
                    Route,
                    path="users/:userId",
                    element=createElement(Outlet),
                    children=[
                        createElement(Route, path="details", element=createElement(_resolved_path_route_relative_probe)),
                        createElement(Route, path="details-path", element=createElement(_resolved_path_path_relative_probe)),
                    ],
                ),
            ),
        ),
        initialEntries=["/users/42/details-path"],
    )

    path_relative_output = renderToString(app, columns=20, rows=5)
    assert "path:/users/42" in path_relative_output


def test_navigate_component_redirects_on_real_render() -> None:
    stdout = _FakeStdout()
    stdin = _FakeStdin()
    app = render(
        createElement(
            MemoryRouter,
            createElement(
                Routes,
                createElement(Route, path="/", element=createElement(Navigate, to="/about", replace=True)),
                createElement(Route, path="/about", element=createElement(_about)),
            ),
            initialEntries=["/"],
        ),
        stdout=stdout,
        stdin=stdin,
        debug=True,
    )

    try:
        time.sleep(0.05)
        app.wait_until_render_flush(timeout=0.3)
        assert "About" in stdout.getvalue()
    finally:
        app.unmount()
