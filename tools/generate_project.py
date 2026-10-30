#!/usr/bin/env python3
"""Generate DashSurf.xcodeproj/project.pbxproj from the DashSurf source tree."""
from __future__ import annotations

import hashlib
import os
import re
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "DashSurf"
TESTS = ROOT / "DashSurfTests"
PROJ = ROOT / "DashSurf.xcodeproj" / "project.pbxproj"

PBX_TYPES = {
    ".swift": "sourcecode.swift",
    ".plist": "text.plist.xml",
    ".entitlements": "text.plist.entitlements",
    ".xcassets": "folder.assetcatalog",
    ".json": "text.json",
    ".md": "net.daringfireball.markdown",
}


def uid(seed: str) -> str:
    h = hashlib.md5(seed.encode()).hexdigest().upper()
    return h[:24]


def pbx_string(value: str) -> str:
    """Quote values Xcode's project parser will not accept unquoted.

    Unquoted tokens may contain letters, digits, and ._/- . A '+' (as in
    URL+DashSurf.swift) is a parse error and the project will not open.
    """
    if re.fullmatch(r"[A-Za-z0-9._/-]+", value):
        return value
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def collect_files(base: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(base.rglob("*")):
        if path.is_dir():
            if path.name.endswith(".xcassets"):
                files.append(path)
            continue
        if path.suffix in {".swift", ".plist", ".entitlements"}:
            files.append(path)
        elif path.name == "Contents.json" and "Assets.xcassets" in str(path):
            # asset catalogs are referenced as folders, not individual json
            continue
    return files


def main() -> None:
    app_files = collect_files(SRC)
    test_files = [p for p in collect_files(TESTS) if p.suffix == ".swift"]

    # Prefer referencing Assets.xcassets as a unit
    app_files = [
        p
        for p in app_files
        if "Assets.xcassets" not in p.parts
        or p.name.endswith(".xcassets")
    ]
    assets = SRC / "Resources" / "Assets.xcassets"
    if assets.exists() and assets not in app_files:
        app_files.append(assets)

    file_refs: dict[Path, str] = {}
    build_files: dict[Path, str] = {}
    for p in app_files + test_files:
        file_refs[p] = uid(f"fileref:{p.relative_to(ROOT)}")
        build_files[p] = uid(f"buildfile:{p.relative_to(ROOT)}")

    project_id = uid("project")
    target_app = uid("target:app")
    target_tests = uid("target:tests")
    sources_app = uid("sources:app")
    sources_tests = uid("sources:tests")
    resources_app = uid("resources:app")
    frameworks = uid("frameworks")
    product_app = uid("product:app")
    product_tests = uid("product:tests")
    group_root = uid("group:root")
    group_products = uid("group:products")
    group_src = uid("group:src")
    group_tests = uid("group:tests")
    config_list_proj = uid("cfgl:proj")
    config_list_app = uid("cfgl:app")
    config_list_tests = uid("cfgl:tests")
    cfg_proj_debug = uid("cfg:proj:debug")
    cfg_proj_release = uid("cfg:proj:release")
    cfg_app_debug = uid("cfg:app:debug")
    cfg_app_release = uid("cfg:app:release")
    cfg_tests_debug = uid("cfg:tests:debug")
    cfg_tests_release = uid("cfg:tests:release")
    dependency = uid("dependency:tests")
    proxy = uid("proxy:tests")

    # Build nested groups mirroring folders under DashSurf/
    groups: dict[str, str] = {"": group_src}
    group_children: dict[str, list[str]] = {"": []}

    def ensure_group(rel: str) -> str:
        if rel in groups:
            return groups[rel]
        gid = uid(f"group:{rel}")
        groups[rel] = gid
        group_children[rel] = []
        parent = str(Path(rel).parent) if Path(rel).parent != Path(".") else ""
        if parent == ".":
            parent = ""
        ensure_group(parent)
        name = Path(rel).name
        group_children[parent].append((gid, name, "group", rel))
        return gid

    file_entries_by_group: dict[str, list[tuple[str, str]]] = {}

    for path in app_files:
        rel = path.relative_to(SRC)
        parent_rel = str(rel.parent) if rel.parent != Path(".") else ""
        if parent_rel == ".":
            parent_rel = ""
        ensure_group(parent_rel)
        file_entries_by_group.setdefault(parent_rel, []).append(
            (file_refs[path], path.name)
        )

    # Flat test group
    for path in test_files:
        file_entries_by_group.setdefault("__tests__", []).append(
            (file_refs[path], path.name)
        )

    lines: list[str] = []
    a = lines.append
    a("// !$*UTF8*$!")
    a("{")
    a("\tarchiveVersion = 1;")
    a("\tclasses = {};")
    a("\tobjectVersion = 56;")
    a("\tobjects = {")
    a("")

    # PBXBuildFile
    a("/* Begin PBXBuildFile section */")
    for path in app_files:
        if path.suffix == ".swift":
            a(
                f"\t\t{build_files[path]} /* {path.name} in Sources */ = "
                f"{{isa = PBXBuildFile; fileRef = {file_refs[path]} /* {path.name} */; }};"
            )
        elif path.name.endswith(".xcassets") or path.suffix in {".plist"} and path.name != "Info.plist":
            if path.name.endswith(".xcassets"):
                a(
                    f"\t\t{build_files[path]} /* {path.name} in Resources */ = "
                    f"{{isa = PBXBuildFile; fileRef = {file_refs[path]} /* {path.name} */; }};"
                )
    for path in test_files:
        a(
            f"\t\t{build_files[path]} /* {path.name} in Sources */ = "
            f"{{isa = PBXBuildFile; fileRef = {file_refs[path]} /* {path.name} */; }};"
        )
    a("/* End PBXBuildFile section */")
    a("")

    # PBXFileReference
    a("/* Begin PBXFileReference section */")
    a(
        f"\t\t{product_app} /* DashSurf.app */ = {{isa = PBXFileReference; explicitFileType = wrapper.application; includeInIndex = 0; path = DashSurf.app; sourceTree = BUILT_PRODUCTS_DIR; }};"
    )
    a(
        f"\t\t{product_tests} /* DashSurfTests.xctest */ = {{isa = PBXFileReference; explicitFileType = wrapper.cfbundle; includeInIndex = 0; path = DashSurfTests.xctest; sourceTree = BUILT_PRODUCTS_DIR; }};"
    )
    for path in app_files + test_files:
        if path.name.endswith(".xcassets"):
            last = "folder.assetcatalog"
        else:
            last = PBX_TYPES.get(path.suffix, "text")
        rel_path = path.relative_to(ROOT).as_posix()
        # Use path relative to group; store full relative for simplicity via name only in groups
        a(
            f"\t\t{file_refs[path]} /* {path.name} */ = {{isa = PBXFileReference; lastKnownFileType = {last}; path = {pbx_string(path.name)}; sourceTree = \"<group>\"; }};"
        )
    a("/* End PBXFileReference section */")
    a("")

    # PBXFrameworksBuildPhase
    a("/* Begin PBXFrameworksBuildPhase section */")
    a(f"\t\t{frameworks} /* Frameworks */ = {{")
    a("\t\t\tisa = PBXFrameworksBuildPhase;")
    a("\t\t\tbuildActionMask = 2147483647;")
    a("\t\t\tfiles = (")
    a("\t\t\t);")
    a("\t\t\trunOnlyForDeploymentPostprocessing = 0;")
    a("\t\t};")
    a("/* End PBXFrameworksBuildPhase section */")
    a("")

    # PBXGroup - rebuild with proper hierarchy using path components
    # Simpler approach: one DashSurf group with nested groups by path

    def emit_group(rel: str, group_id: str, display_name: str, path_name: str | None) -> None:
        children_ids: list[str] = []
        # child groups
        for child_rel, child_id in sorted(
            ((k, v) for k, v in groups.items() if k and str(Path(k).parent).replace("\\", "/") == (rel or ".") or (rel == "" and Path(k).parent == Path("."))),
            key=lambda x: x[0],
        ):
            # Fix parent matching
            pass

    # Rebuild group tree cleanly
    groups.clear()
    groups[""] = group_src
    children_map: dict[str, list[str]] = {"": []}

    def ensure(rel: str) -> str:
        rel = rel.replace("\\", "/")
        if rel in groups:
            return groups[rel]
        parts = rel.split("/")
        cur = ""
        for part in parts:
            parent = cur
            cur = part if cur == "" else f"{cur}/{part}"
            if cur not in groups:
                groups[cur] = uid(f"group:{cur}")
                children_map.setdefault(cur, [])
                children_map.setdefault(parent, [])
                children_map[parent].append(groups[cur])
        return groups[rel]

    file_parent: dict[Path, str] = {}
    for path in app_files:
        rel_parent = path.relative_to(SRC).parent.as_posix()
        if rel_parent == ".":
            rel_parent = ""
        ensure(rel_parent) if rel_parent else None
        if rel_parent:
            ensure(rel_parent)
        file_parent[path] = groups[rel_parent]
        children_map.setdefault(rel_parent, [])
        children_map[rel_parent].append(file_refs[path])

    a("/* Begin PBXGroup section */")
    a(f"\t\t{group_root} = {{")
    a("\t\t\tisa = PBXGroup;")
    a("\t\t\tchildren = (")
    a(f"\t\t\t\t{group_src} /* DashSurf */,")
    a(f"\t\t\t\t{group_tests} /* DashSurfTests */,")
    a(f"\t\t\t\t{group_products} /* Products */,")
    a("\t\t\t);")
    a('\t\t\tsourceTree = "<group>";')
    a("\t\t};")

    a(f"\t\t{group_products} /* Products */ = {{")
    a("\t\t\tisa = PBXGroup;")
    a("\t\t\tchildren = (")
    a(f"\t\t\t\t{product_app} /* DashSurf.app */,")
    a(f"\t\t\t\t{product_tests} /* DashSurfTests.xctest */,")
    a("\t\t\t);")
    a("\t\t\tname = Products;")
    a('\t\t\tsourceTree = "<group>";')
    a("\t\t};")

    # Emit all source groups
    for rel, gid in sorted(groups.items(), key=lambda x: x[0]):
        name = "DashSurf" if rel == "" else Path(rel).name
        a(f"\t\t{gid} /* {name} */ = {{")
        a("\t\t\tisa = PBXGroup;")
        a("\t\t\tchildren = (")
        # unique preserve order
        seen = set()
        for child in children_map.get(rel, []):
            if child in seen:
                continue
            seen.add(child)
            a(f"\t\t\t\t{child},")
        a("\t\t\t);")
        if rel == "":
            a("\t\t\tpath = DashSurf;")
        else:
            a(f"\t\t\tpath = {Path(rel).name};")
        a('\t\t\tsourceTree = "<group>";')
        a("\t\t};")

    a(f"\t\t{group_tests} /* DashSurfTests */ = {{")
    a("\t\t\tisa = PBXGroup;")
    a("\t\t\tchildren = (")
    for path in test_files:
        a(f"\t\t\t\t{file_refs[path]} /* {path.name} */,")
    a("\t\t\t);")
    a("\t\t\tpath = DashSurfTests;")
    a('\t\t\tsourceTree = "<group>";')
    a("\t\t};")
    a("/* End PBXGroup section */")
    a("")

    # Native targets
    a("/* Begin PBXNativeTarget section */")
    a(f"\t\t{target_app} /* DashSurf */ = {{")
    a("\t\t\tisa = PBXNativeTarget;")
    a(f"\t\t\tbuildConfigurationList = {config_list_app} /* Build configuration list for PBXNativeTarget \"DashSurf\" */;")
    a("\t\t\tbuildPhases = (")
    a(f"\t\t\t\t{sources_app} /* Sources */,")
    a(f"\t\t\t\t{frameworks} /* Frameworks */,")
    a(f"\t\t\t\t{resources_app} /* Resources */,")
    a("\t\t\t);")
    a("\t\t\tbuildRules = (")
    a("\t\t\t);")
    a("\t\t\tdependencies = (")
    a("\t\t\t);")
    a("\t\t\tname = DashSurf;")
    a("\t\t\tproductName = DashSurf;")
    a(f"\t\t\tproductReference = {product_app} /* DashSurf.app */;")
    a('\t\t\tproductType = "com.apple.product-type.application";')
    a("\t\t};")

    a(f"\t\t{target_tests} /* DashSurfTests */ = {{")
    a("\t\t\tisa = PBXNativeTarget;")
    a(f"\t\t\tbuildConfigurationList = {config_list_tests} /* Build configuration list for PBXNativeTarget \"DashSurfTests\" */;")
    a("\t\t\tbuildPhases = (")
    a(f"\t\t\t\t{sources_tests} /* Sources */,")
    a(f"\t\t\t\t{frameworks} /* Frameworks */,")
    a("\t\t\t);")
    a("\t\t\tbuildRules = (")
    a("\t\t\t);")
    a("\t\t\tdependencies = (")
    a(f"\t\t\t\t{dependency} /* PBXTargetDependency */,")
    a("\t\t\t);")
    a("\t\t\tname = DashSurfTests;")
    a("\t\t\tproductName = DashSurfTests;")
    a(f"\t\t\tproductReference = {product_tests} /* DashSurfTests.xctest */;")
    a('\t\t\tproductType = "com.apple.product-type.bundle.unit-test";')
    a("\t\t};")
    a("/* End PBXNativeTarget section */")
    a("")

    # Project
    a("/* Begin PBXProject section */")
    a(f"\t\t{project_id} /* Project object */ = {{")
    a("\t\t\tisa = PBXProject;")
    a("\t\t\tattributes = {")
    a("\t\t\t\tBuildIndependentTargetsInParallel = 1;")
    a('\t\t\t\tLastSwiftUpdateCheck = 1600;')
    a("\t\t\t\tLastUpgradeCheck = 1600;")
    a("\t\t\t\tTargetAttributes = {")
    a(f"\t\t\t\t\t{target_app} = {{")
    a("\t\t\t\t\t\tCreatedOnToolsVersion = 16.0;")
    a("\t\t\t\t\t};")
    a(f"\t\t\t\t\t{target_tests} = {{")
    a("\t\t\t\t\t\tCreatedOnToolsVersion = 16.0;")
    a("\t\t\t\t\t\tTestTargetID = " + target_app + ";")
    a("\t\t\t\t\t};")
    a("\t\t\t\t};")
    a("\t\t\t};")
    a(f"\t\t\tbuildConfigurationList = {config_list_proj} /* Build configuration list for PBXProject \"DashSurf\" */;")
    a('\t\t\tcompatibilityVersion = "Xcode 15.0";')
    a("\t\t\tdevelopmentRegion = en;")
    a("\t\t\thasScannedForEncodings = 0;")
    a("\t\t\tknownRegions = (")
    a("\t\t\t\ten,")
    a("\t\t\t\tBase,")
    a("\t\t\t);")
    a(f"\t\t\tmainGroup = {group_root};")
    a(f"\t\t\tproductRefGroup = {group_products} /* Products */;")
    a('\t\t\tprojectDirPath = "";')
    a('\t\t\tprojectRoot = "";')
    a("\t\t\ttargets = (")
    a(f"\t\t\t\t{target_app} /* DashSurf */,")
    a(f"\t\t\t\t{target_tests} /* DashSurfTests */,")
    a("\t\t\t);")
    a("\t\t};")
    a("/* End PBXProject section */")
    a("")

    # Resources
    a("/* Begin PBXResourcesBuildPhase section */")
    a(f"\t\t{resources_app} /* Resources */ = {{")
    a("\t\t\tisa = PBXResourcesBuildPhase;")
    a("\t\t\tbuildActionMask = 2147483647;")
    a("\t\t\tfiles = (")
    for path in app_files:
        if path.name.endswith(".xcassets"):
            a(f"\t\t\t\t{build_files[path]} /* {path.name} in Resources */,")
    a("\t\t\t);")
    a("\t\t\trunOnlyForDeploymentPostprocessing = 0;")
    a("\t\t};")
    a("/* End PBXResourcesBuildPhase section */")
    a("")

    # Sources
    a("/* Begin PBXSourcesBuildPhase section */")
    a(f"\t\t{sources_app} /* Sources */ = {{")
    a("\t\t\tisa = PBXSourcesBuildPhase;")
    a("\t\t\tbuildActionMask = 2147483647;")
    a("\t\t\tfiles = (")
    for path in app_files:
        if path.suffix == ".swift":
            a(f"\t\t\t\t{build_files[path]} /* {path.name} in Sources */,")
    a("\t\t\t);")
    a("\t\t\trunOnlyForDeploymentPostprocessing = 0;")
    a("\t\t};")
    a(f"\t\t{sources_tests} /* Sources */ = {{")
    a("\t\t\tisa = PBXSourcesBuildPhase;")
    a("\t\t\tbuildActionMask = 2147483647;")
    a("\t\t\tfiles = (")
    for path in test_files:
        a(f"\t\t\t\t{build_files[path]} /* {path.name} in Sources */,")
    a("\t\t\t);")
    a("\t\t\trunOnlyForDeploymentPostprocessing = 0;")
    a("\t\t};")
    a("/* End PBXSourcesBuildPhase section */")
    a("")

    # XCBuildConfiguration
    a("/* Begin XCBuildConfiguration section */")

    def proj_cfg(cid: str, name: str) -> None:
        a(f"\t\t{cid} /* {name} */ = {{")
        a("\t\t\tisa = XCBuildConfiguration;")
        a("\t\t\tbuildSettings = {")
        a("\t\t\t\tALWAYS_SEARCH_USER_PATHS = NO;")
        a("\t\t\t\tCLANG_ENABLE_MODULES = YES;")
        a("\t\t\t\tCLANG_ENABLE_OBJC_ARC = YES;")
        a('\t\t\t\tCOPY_PHASE_STRIP = NO;')
        a("\t\t\t\tDEBUG_INFORMATION_FORMAT = dwarf;")
        a("\t\t\t\tENABLE_STRICT_OBJC_MSGSEND = YES;")
        a("\t\t\t\tGCC_DYNAMIC_NO_PIC = NO;")
        a('\t\t\t\tIPHONEOS_DEPLOYMENT_TARGET = 17.0;')
        a("\t\t\t\tMTL_ENABLE_DEBUG_INFO = INCLUDE_SOURCE;" if name == "Debug" else "\t\t\t\tMTL_ENABLE_DEBUG_INFO = NO;")
        a("\t\t\t\tONLY_ACTIVE_ARCH = YES;" if name == "Debug" else "\t\t\t\tONLY_ACTIVE_ARCH = NO;")
        a("\t\t\t\tSDKROOT = iphoneos;")
        a('\t\t\t\tSWIFT_VERSION = 5.0;')
        if name == "Debug":
            a("\t\t\t\tSWIFT_ACTIVE_COMPILATION_CONDITIONS = DEBUG;")
            a("\t\t\t\tSWIFT_OPTIMIZATION_LEVEL = \"-Onone\";")
            a("\t\t\t\tGCC_PREPROCESSOR_DEFINITIONS = (")
            a('\t\t\t\t\t"DEBUG=1",')
            a("\t\t\t\t\t\"$(inherited)\",")
            a("\t\t\t\t);")
        else:
            a("\t\t\t\tSWIFT_COMPILATION_MODE = wholemodule;")
            a("\t\t\t\tVALIDATE_PRODUCT = YES;")
        a("\t\t\t};")
        a(f'\t\t\tname = {name};')
        a("\t\t};")

    proj_cfg(cfg_proj_debug, "Debug")
    proj_cfg(cfg_proj_release, "Release")

    def app_cfg(cid: str, name: str) -> None:
        a(f"\t\t{cid} /* {name} */ = {{")
        a("\t\t\tisa = XCBuildConfiguration;")
        a("\t\t\tbuildSettings = {")
        a('\t\t\t\tASSETCATALOG_COMPILER_APPICON_NAME = AppIcon;')
        a("\t\t\t\tASSETCATALOG_COMPILER_GLOBAL_ACCENT_COLOR_NAME = AccentColor;")
        a("\t\t\t\tCODE_SIGN_STYLE = Automatic;")
        a('\t\t\t\tCURRENT_PROJECT_VERSION = 1;')
        a(f"\t\t\t\tDEVELOPMENT_TEAM = {pbx_string(os.environ.get('DASHSURF_TEAM', '5T35H63YR2'))};")
        a("\t\t\t\tENABLE_PREVIEWS = YES;")
        a("\t\t\t\tGENERATE_INFOPLIST_FILE = NO;")
        a('\t\t\t\tINFOPLIST_FILE = DashSurf/Info.plist;')
        a('\t\t\t\tINFOPLIST_KEY_CFBundleDisplayName = DashSurf;')
        a('\t\t\t\tINFOPLIST_KEY_LSApplicationCategoryType = "public.app-category.productivity";')
        a('\t\t\t\tIPHONEOS_DEPLOYMENT_TARGET = 17.0;')
        a('\t\t\t\tLD_RUNPATH_SEARCH_PATHS = (')
        a('\t\t\t\t\t"$(inherited)",')
        a('\t\t\t\t\t"@executable_path/Frameworks",')
        a("\t\t\t\t);")
        a("\t\t\t\tMARKETING_VERSION = 1.0.0;")
        a('\t\t\t\tPRODUCT_BUNDLE_IDENTIFIER = com.joannadutka.dashsurf;')
        a("\t\t\t\tPRODUCT_NAME = \"$(TARGET_NAME)\";")
        a("\t\t\t\tSUPPORTED_PLATFORMS = \"iphoneos iphonesimulator\";")
        a('\t\t\t\tSUPPORTS_MACCATALYST = NO;')
        a("\t\t\t\tSWIFT_EMIT_LOC_STRINGS = YES;")
        a('\t\t\t\tSWIFT_VERSION = 5.0;')
        a("\t\t\t\tTARGETED_DEVICE_FAMILY = \"1,2\";")
        a('\t\t\t\tCODE_SIGN_ENTITLEMENTS = DashSurf/DashSurf.entitlements;')
        a("\t\t\t};")
        a(f'\t\t\tname = {name};')
        a("\t\t};")

    app_cfg(cfg_app_debug, "Debug")
    app_cfg(cfg_app_release, "Release")

    def test_cfg(cid: str, name: str) -> None:
        a(f"\t\t{cid} /* {name} */ = {{")
        a("\t\t\tisa = XCBuildConfiguration;")
        a("\t\t\tbuildSettings = {")
        a("\t\t\t\tBUNDLE_LOADER = \"$(TEST_HOST)\";")
        a("\t\t\t\tCODE_SIGN_STYLE = Automatic;")
        a('\t\t\t\tCURRENT_PROJECT_VERSION = 1;')
        a(f"\t\t\t\tDEVELOPMENT_TEAM = {pbx_string(os.environ.get('DASHSURF_TEAM', '5T35H63YR2'))};")
        a("\t\t\t\tGENERATE_INFOPLIST_FILE = YES;")
        a('\t\t\t\tIPHONEOS_DEPLOYMENT_TARGET = 17.0;')
        a("\t\t\t\tMARKETING_VERSION = 1.0.0;")
        a('\t\t\t\tPRODUCT_BUNDLE_IDENTIFIER = com.joannadutka.dashsurf.tests;')
        a("\t\t\t\tPRODUCT_NAME = \"$(TARGET_NAME)\";")
        a('\t\t\t\tSWIFT_VERSION = 5.0;')
        a("\t\t\t\tTARGETED_DEVICE_FAMILY = \"1,2\";")
        a('\t\t\t\tTEST_HOST = "$(BUILT_PRODUCTS_DIR)/DashSurf.app/$(BUNDLE_EXECUTABLE_FOLDER_PATH)/DashSurf";')
        a("\t\t\t};")
        a(f'\t\t\tname = {name};')
        a("\t\t};")

    test_cfg(cfg_tests_debug, "Debug")
    test_cfg(cfg_tests_release, "Release")
    a("/* End XCBuildConfiguration section */")
    a("")

    a("/* Begin XCConfigurationList section */")
    a(f"\t\t{config_list_proj} /* Build configuration list for PBXProject \"DashSurf\" */ = {{")
    a("\t\t\tisa = XCConfigurationList;")
    a("\t\t\tbuildConfigurations = (")
    a(f"\t\t\t\t{cfg_proj_debug} /* Debug */,")
    a(f"\t\t\t\t{cfg_proj_release} /* Release */,")
    a("\t\t\t);")
    a("\t\t\tdefaultConfigurationIsVisible = 0;")
    a('\t\t\tdefaultConfigurationName = Release;')
    a("\t\t};")
    a(f"\t\t{config_list_app} /* Build configuration list for PBXNativeTarget \"DashSurf\" */ = {{")
    a("\t\t\tisa = XCConfigurationList;")
    a("\t\t\tbuildConfigurations = (")
    a(f"\t\t\t\t{cfg_app_debug} /* Debug */,")
    a(f"\t\t\t\t{cfg_app_release} /* Release */,")
    a("\t\t\t);")
    a("\t\t\tdefaultConfigurationIsVisible = 0;")
    a('\t\t\tdefaultConfigurationName = Release;')
    a("\t\t};")
    a(f"\t\t{config_list_tests} /* Build configuration list for PBXNativeTarget \"DashSurfTests\" */ = {{")
    a("\t\t\tisa = XCConfigurationList;")
    a("\t\t\tbuildConfigurations = (")
    a(f"\t\t\t\t{cfg_tests_debug} /* Debug */,")
    a(f"\t\t\t\t{cfg_tests_release} /* Release */,")
    a("\t\t\t);")
    a("\t\t\tdefaultConfigurationIsVisible = 0;")
    a('\t\t\tdefaultConfigurationName = Release;')
    a("\t\t};")
    a("/* End XCConfigurationList section */")
    a("")
    a("/* Begin PBXTargetDependency section */")
    a(f"\t\t{dependency} /* PBXTargetDependency */ = {{")
    a("\t\t\tisa = PBXTargetDependency;")
    a(f"\t\t\ttarget = {target_app} /* DashSurf */;")
    a(f"\t\t\ttargetProxy = {proxy} /* PBXContainerItemProxy */;")
    a("\t\t};")
    a("/* End PBXTargetDependency section */")
    a("")
    a("/* Begin PBXContainerItemProxy section */")
    a(f"\t\t{proxy} /* PBXContainerItemProxy */ = {{")
    a("\t\t\tisa = PBXContainerItemProxy;")
    a(f"\t\t\tcontainerPortal = {project_id} /* Project object */;")
    a("\t\t\tproxyType = 1;")
    a(f"\t\t\tremoteGlobalIDString = {target_app};")
    a("\t\t\tremoteInfo = DashSurf;")
    a("\t\t};")
    a("/* End PBXContainerItemProxy section */")
    a("\t};")
    a(f"\trootObject = {project_id} /* Project object */;")
    a("}")

    PROJ.parent.mkdir(parents=True, exist_ok=True)
    PROJ.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {PROJ}")
    print(f"App sources: {sum(1 for p in app_files if p.suffix=='.swift')}")
    print(f"Test sources: {len(test_files)}")


if __name__ == "__main__":
    main()
