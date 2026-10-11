"""Verdict rules for the security checks (judgment only; see verdicts.py for the contract).

Each rule's text is the human-readable spec in `docs/verdict-rules.md`, which stays authoritative on intent. A fact
that is missing from the bundle is Needs Review, never an assumed Fail: the bundle may simply not carry the setting."""
from __future__ import annotations

from verdicts import ABSENT, _missing, fact, rule, verdict


@rule("SEC-001", "Verify/Capture Instance IDs")
def instance_id(facts):
    node = fact(facts, "node")
    if not isinstance(node, dict):
        return _missing("node information")
    installid = node.get("installid", ABSENT)
    if installid == ABSENT:
        return verdict("Fail", "no instance (install) id in the bundle", installid=ABSENT)
    return verdict("Pass", f"instance id present ({installid})", installid=installid)


@rule("SEC-002", "User Isolation Framework (UIF) Enabled with Appropriate Impersonation Rules")
def user_isolation(facts):
    uif = fact(facts, "user_isolation")
    if not isinstance(uif, dict):
        return _missing("impersonation settings")
    enabled, rules = uif.get("enabled", ABSENT), (uif.get("user_rules") or 0) + (uif.get("group_rules") or 0)
    values = {"enabled": enabled, "rules": rules}
    if enabled is False:
        return verdict("Fail", "UIF is disabled", **values)
    if enabled is not True:
        return _missing("the UIF enabled flag")
    if rules >= 1:
        return verdict("Pass", f"UIF enabled with {rules} impersonation rule(s)", **values)
    return verdict("Partial", "UIF enabled but no user or group rules", **values)


def _sso_ldap(facts):
    block = fact(facts, "sso_and_ldap")
    return block if isinstance(block, dict) else None


@rule("SEC-009", "LDAP Authorized Groups Configured")
def ldap_authorized_groups(facts):
    block = _sso_ldap(facts)
    if block is None:
        return _missing("LDAP settings")
    ldap, count = block.get("ldapSettings.enabled", ABSENT), block.get("ldapSettings.authorizedGroups_count", ABSENT)
    values = {"ldap_enabled": ldap, "authorized_groups": count}
    if ldap is False:
        return verdict("Not Applicable", "LDAP is not enabled", **values)
    if ldap is not True or not isinstance(count, int):
        return _missing("the LDAP enabled flag or authorized-group count")
    if count >= 1:
        return verdict("Pass", f"LDAP enabled with {count} authorized group(s)", **values)
    return verdict("Needs Review", "LDAP enabled with no authorized groups (ask whether intentional)", **values)


@rule("SEC-010", "SSO Enablement Reviewed")
def sso_enabled(facts):
    block = _sso_ldap(facts)
    if block is None:
        return _missing("SSO and LDAP settings")
    sso = block.get("ssoSettings.enabled", ABSENT)
    values = {"sso_enabled": sso, "sso_protocol": block.get("ssoSettings.protocol", ABSENT)}
    if sso is True:
        return verdict("Pass", "SSO is enabled", **values)
    if sso is False:
        return verdict("Fail", "SSO is disabled", **values)
    return _missing("the SSO enabled flag")


@rule("SEC-005", "JEK-Specific CGroup Limits Left Unconfigured")
def jek_cgroup_unconfigured(facts):
    cg = fact(facts, "cgroups")
    counts = cg.get("target_counts") if isinstance(cg, dict) else None
    if not isinstance(counts, dict):
        return _missing("cgroup settings")
    jek = counts.get("jobExecutionKernels")  # absent key = no JEK category configured at all
    if jek:
        return verdict("Fail", f"{jek} JEK-specific cgroup target(s) configured", jek_targets=jek)
    return verdict("Pass", "no JEK-specific cgroup target", jek_targets=jek if jek is not None else 0)


# --- the instance's `security` settings block (Batch 3a) ------------------------------------------------------------
#
# Policy (docs/verdict-rules.md, Security): a secure toggle that is on is Pass; one that is off is Fail, except where the
# checklist itself allows a deliberate choice (ADVSEC-010, 012, SEC-007), which is Needs Review (ask for the
# documented need). A setting missing from the bundle is Needs Review.

def _security(facts):
    block = fact(facts, "security_settings")
    return block if isinstance(block, dict) else None


def _toggle(facts, key, *, want, off_status, label):
    """Pass when `key` equals `want`; otherwise `off_status`; Needs Review when the setting is missing."""
    sec = _security(facts)
    if sec is None:
        return _missing("security settings")
    value = sec.get(key, ABSENT)
    if not isinstance(value, bool):
        return _missing(f"{key}")
    if value is want:
        return verdict("Pass", f"{label}: {key}={str(value).lower()}", **{key: value})
    reason = f"expected {label}, but {key}={str(value).lower()}"
    if off_status == "Needs Review":
        reason += " (ask whether intentional)"
    return verdict(off_status, reason, **{key: value})


@rule("ADVSEC-001", "Hiding error stacks")
def hide_error_stacks(facts):
    return _toggle(facts, "hideErrorStacks", want=True, off_status="Fail", label="error stacks are hidden")


@rule("ADVSEC-002", "Hiding version info")
def hide_version_info(facts):
    return _toggle(facts, "hideVersionStringsWhenNotLogged", want=True, off_status="Fail", label="version info is hidden before login")


@rule("ADVSEC-003", "Expiring sessions")
def expiring_sessions(facts):
    sec = _security(facts)
    if sec is None:
        return _missing("security settings")
    total, idle = sec.get("sessionsMaxTotalTimeMinutes", ABSENT), sec.get("sessionsMaxIdleTimeMinutes", ABSENT)
    values = {"sessionsMaxTotalTimeMinutes": total, "sessionsMaxIdleTimeMinutes": idle}
    nums = [v for v in (total, idle) if isinstance(v, int) and not isinstance(v, bool)]
    if any(v > 0 for v in nums):
        return verdict("Pass", "a session timeout is set (0 means unlimited)", **values)
    if len(nums) == 2:
        return verdict("Fail", "both session timeouts are 0 (unlimited)", **values)
    return _missing("the session timeout settings")


@rule("ADVSEC-004", "Forcing a single session per user")
def single_session(facts):
    return _toggle(facts, "forceSingleSessionPerUser", want=True, off_status="Fail", label="one session per user is forced")


@rule("ADVSEC-005", "Restricting visibility of groups and users")
def restrict_visibility(facts):
    return _toggle(facts, "restrictUsersAndGroupsVisibility", want=True, off_status="Fail",
                   label="users and groups are hidden from other users")


@rule("ADVSEC-006", "Redirecting to a custom URL after logout")
def post_logout_redirect(facts):
    sec = _security(facts)
    if sec is None:
        return _missing("security settings")
    behavior, scheme = sec.get("postLogoutBehavior", ABSENT), sec.get("postLogoutCustomURL_scheme", ABSENT)
    values = {"postLogoutBehavior": behavior, "postLogoutCustomURL_scheme": scheme}
    if behavior in ("CUSTOM_URL", "CUSTOM_URL_POST"):
        if scheme in ("http", "https"):
            return verdict("Pass", f"a custom logout redirect is configured ({scheme} URL)", **values)
        return verdict("Needs Review", "a custom logout redirect is configured but its URL is not http or https", **values)
    if behavior in ("LOGGED_OUT_PAGE", ABSENT):
        return verdict("Pass", "no custom logout redirect; the default logged-out page is used", **values)
    return verdict("Needs Review", f"unrecognised logout behaviour ({behavior})", **values)


@rule("ADVSEC-010", "Allowing DSS to be hosted inside an iframe")
def iframe_hosting(facts):
    sec = _security(facts)
    if sec is None:
        return _missing("security settings")
    same_site, secure = sec.get("sameSiteNoneCookies", ABSENT), sec.get("secureCookies", ABSENT)
    values = {"sameSiteNoneCookies": same_site, "secureCookies": secure}
    if not isinstance(same_site, bool):
        return _missing("sameSiteNoneCookies")
    if same_site is False:
        return verdict("Pass", "iframe hosting is not enabled (sameSiteNoneCookies=false)", **values)
    if secure is False:
        return verdict("Fail", "iframe hosting is enabled without secure cookies", **values)
    return verdict("Needs Review", "iframe hosting is enabled (ask for the documented need)", **values)


@rule("ADVSEC-012", "Allowing DSS users to edit their display names and emails")
def users_edit_profile(facts):
    return _toggle(facts, "enableEmailAndDisplayNameModification", want=False, off_status="Needs Review",
                   label="users cannot edit their display name and email")


@rule("SEC-007", "Secure Cookies Enabled (security.secureCookies)")
def secure_cookies(facts):
    return _toggle(facts, "secureCookies", want=True, off_status="Needs Review", label="cookies are marked secure")


# --- HTTPS, exports, uploads, links and security headers (Batch 3b; the reader's `server_config` fact) -----------------

def _server(facts):
    block = fact(facts, "server_config")
    return block if isinstance(block, dict) else None


@rule("SEC-006", "HTTPS Access Configured for DSS")
def https_configured(facts):
    cfg = _server(facts)
    if cfg is None:
        return _missing("the server settings")
    ssl, cert = str(cfg.get("ssl", ABSENT)).lower(), cfg.get("ssl_certificate_configured") is True
    values = {"ssl": cfg.get("ssl", ABSENT), "certificate_configured": cert}
    if ssl == "true" and cert:
        return verdict("Pass", "DSS terminates TLS itself (ssl on, certificate configured)", **values)
    return verdict("Needs Review", "DSS itself is not configured for HTTPS; a TLS-terminating proxy can't be ruled out", **values)


@rule("ADVSEC-007", "Restricting types of files that can be uploaded in wikis")
def wiki_upload_extensions(facts):
    cfg = _server(facts)
    if cfg is None:
        return _missing("the server settings")
    exts = cfg.get("wiki_upload_extensions", ABSENT)
    if exts != ABSENT and str(exts).strip():
        return verdict("Pass", "wiki uploads are restricted to a list of extensions", wiki_upload_extensions=exts)
    return verdict("Fail", "no wiki upload restriction set (the default allows any file type)", wiki_upload_extensions=ABSENT)


@rule("ADVSEC-008", "Restricting exports")
def export_restriction(facts):
    cfg = _server(facts)
    if cfg is None:
        return _missing("the server settings")
    exports = cfg.get("exports") if isinstance(cfg.get("exports"), dict) else {}
    on = sorted(k for k, v in exports.items() if str(v).strip().lower() == "true")
    if on:
        return verdict("Pass", f"export restriction set ({on[0]}=true)", exports_enabled=on)
    return verdict("Fail", "no export restriction set", exports_enabled=[])


_CORE_HEADERS = ("content-security-policy", "x-frame-options", "x-content-type-options", "x-xss-protection", "hsts-max-age", "referrer-policy")


def _restrictive(name, value):
    value = str(value).strip()
    if name == "x-frame-options":
        return value.upper() in ("SAMEORIGIN", "DENY")
    if name == "x-content-type-options":
        return value.lower() == "nosniff"
    if name == "x-xss-protection":
        return bool(value) and not value.startswith("0")
    if name == "hsts-max-age":
        return value.isdigit() and int(value) > 0
    return bool(value)


@rule("ADVSEC-009", "Setting security-related HTTP headers")
def security_headers(facts):
    cfg = _server(facts)
    if cfg is None:
        return _missing("the server settings")
    headers = cfg.get("security_headers") if isinstance(cfg.get("security_headers"), dict) else {}
    good = [h for h in _CORE_HEADERS if h in headers and _restrictive(h, headers[h])]
    values = {"headers_set": sorted(headers), "core_headers_restrictive": good,
              "core_headers_missing_or_weak": [h for h in _CORE_HEADERS if h not in good]}
    if not headers:
        return verdict("Fail", "no security header configured in DSS (a proxy may set them)", **values)
    if len(good) == len(_CORE_HEADERS):
        return verdict("Pass", "all six core security headers set with restrictive values", **values)
    return verdict("Partial", f"{len(good)} of 6 core security headers set with restrictive values", **values)


@rule("ADVSEC-011", "Preventing links to be clickable in data tables")
def data_table_links(facts):
    sec, cfg = _security(facts), _server(facts)
    flag = sec.get("disableDataTableLinks", ABSENT) if sec else ABSENT
    dip_off = bool(cfg) and str(cfg.get("data_table_links_enabled", ABSENT)).strip().lower() == "false"
    values = {"disableDataTableLinks": flag, "dataTableLinks_enabled_in_properties": cfg.get("data_table_links_enabled", ABSENT) if cfg else ABSENT}
    if flag is True or dip_off:
        return verdict("Pass", "links in data tables are disabled", **values)
    if flag is False:
        return verdict("Needs Review", "links in data tables are not disabled (ask whether intentional)", **values)
    return _missing("the data-table links setting")
