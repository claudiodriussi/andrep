# Security

## Reporting a vulnerability

Please report security problems **privately**, through GitHub's private vulnerability
reporting: open the repository's **Security** tab and choose **Report a vulnerability**
(or go to <https://github.com/claudiodriussi/andrep/security/advisories/new>).

Please do not open a public issue for a vulnerability. Include what you need to reproduce
the problem — a template, the loop code, the AndRep version — and what you expected. You
will get an answer as soon as possible; AndRep is maintained by one person, so allow a
few days.

---

## Scope

| Component  | Covered | Notes |
| ---------- | ------- | ----- |
| `renderer/` — the Python engine | yes | Everything in this document |
| `editor/` — the visual designer | yes | It never evaluates expressions; templates it saves are checked by the renderer when loaded |
| `clients/` — loop engines, REST servers | **no** | Demonstrations only: to keep them short, security was left out on purpose (no authentication, open CORS, the JS client evaluates expressions with `new Function`). Do not expose them as they are |

---

## The model in brief

- **A template is data.** It does not run code, does not read files outside the allowed
  places, does not touch anything that is not data.
- **The template reads, the code writes.** Totals, counters and band choices live in the
  loop and in the event hooks — the developer's Python. The template shows. Nothing in a
  report needs an expression that changes state.
- **Safe by default.** `AndRepRenderer(..., trusted=True)` is the explicit way out for
  developers who write their own templates and trust them.

---

## Trust boundary

**Trusted by definition** — code and configuration under the developer's responsibility:

- the loop and the renderer subclass with its hooks;
- everything the developer passes to the renderer: template name, loader, `metadata` of
  `from_compiled()`, `base_dir`, `resolver`, `r.globals`, `r.formatters`, the PDF backend.

If this code is altered, the system is already compromised and no rule of the engine can
help.

**Not trusted** — the **content of the template**: expressions in `[...]`, `cssExtra`
(literal and `@expression`), cell styles, Markdown text, resource references (`@path`,
image URLs), `composition` targets, expression translations.

**Data** — the values of the rows — comes from the loop, but is often written by people
who have no access to code or templates (a customer name, a product description). Data is
never evaluated; markup it may contain is made harmless by the confinement described in
[Resources and the generated document](#resources-and-the-generated-document).

---

## When it matters

As long as the people who edit templates are the people who run the server, a sandbox
protects nothing: they can run code in many other ways. The risk appears when the two
roles differ — none of these cases needs a malicious user:

1. **A stolen credential** — with the web editor in production, editing a template is an
   endpoint behind a login. Whoever steals the password of a user allowed to edit
   templates must not gain access to the server.
2. **Multi-tenant** — a tenant administrator editing their own layouts must not read other
   tenants' data.
3. **An imported template** — "here is my invoice layout": loading it must be safe.

AndRep treats three kinds of risk differently:

| Risk | Examples | How it is treated |
| ---- | -------- | ----------------- |
| **Access to the system** | database, files, internal network, running code | **Closed** by the engine |
| **Exfiltration** | report data sent to a third party | **Reduced**; one residual channel, documented below |
| **Overload** | an expression building a huge string | Left to the **host** (timeouts, memory limits) |

---

## Template expressions

Expressions are a **subset of Python**, parsed and checked when the template is loaded,
and compiled once:

- allowed: literals, names, attribute and index access, arithmetic, comparisons and
  boolean operators, `a if cond else b`, lists / tuples / dicts / sets, calls,
  comprehensions and generator expressions, f-strings;
- not allowed: anything else — function definitions (`lambda`), assignments, unpacking;
- names starting with `_` are not allowed, except the system variables (`_r`, `_page`,
  `_date`, `_time`, `_user`, `_name`); attributes starting with `_` are never allowed;
- no Python built-ins are available: functions a template needs are registered by the
  developer in `r.globals` (**functions, not objects**).

The **namespace holds data only**, always as a copy:

- `str`, `int`, `float`, `bool`, `None`, `Decimal`, `date` / `datetime` / `time` /
  `timedelta`, `bytes`, `list`, `tuple`, `set`, `dict`; dicts and dict-like rows (such as
  `sqlite3.Row`) become objects with attribute access; subclasses are normalized to the
  base type;
- a **local variable** of the loop that is not data (a connection, a cursor, the
  renderer) is left out: the loop keeps working, and a template that uses it shows a
  marker saying so;
- the **workspace** (`r["key"] = value`) raises `TypeError` on assignment if the value is
  not data;
- `_r` is a **snapshot** of the renderer's public data attributes (accumulators, title,
  metadata): methods of the renderer are not available;
- attributes are read only from data: methods of the base types are available, except
  `str.format` / `str.format_map` (AndRep formatters cover formatting).

An expression that is rejected is **never evaluated**. Rejected or failing expressions
show in the report as `[#expr: reason#]`, where the person who wrote the template looks.

---

## Resources and the generated document

Everything a template refers to — `load`, `img`, image cells, images in Markdown — is read
by the renderer through a **resource resolver** and embedded in the document as a `data:`
URL. The default resolver reads:

- files **inside** `base_dir` (relative paths only; `..`, absolute paths and symlinks
  leading outside are refused);
- files inside **named roots** declared by the developer (`media:2026/09/photo.jpg`);
- `http(s)` URLs of **public** hosts only. The check is made on the address the connection
  is actually made to, for every request, redirects included; system proxies are not
  used.

The generated document fetches nothing by itself:

- the **PDF backends** load `data:` URLs only — WeasyPrint through a URL fetcher that
  refuses anything else; Playwright in its own browser context, with **JavaScript
  disabled** and every network request aborted, also when a shared browser is passed;
- every generated **HTML document** carries a Content-Security-Policy: no scripts, no
  connections, images and fonts only as `data:` URLs, inline styles allowed.

So HTML or CSS written in a template, or found in the data, is only presentation: at worst
an ugly or misleading document. A `url(...)` written in `cssExtra` is not loaded.

---

## Composition and loaders

`composition` targets are template content. `FilesystemLoader` resolves a name only
inside `base_dir` / `custom_dir`: `..`, absolute paths and symlinks leading outside raise
`ValueError`. A target that simply does not exist is skipped (optional overrides).

A custom loader (`TemplateLoader`) must follow the same contract: raise
`FileNotFoundError` for a valid name without a template, raise `ValueError` for a name
outside its own storage — never resolve it.

---

## For integrators

**Resources.** Pass a resolver to the renderer to declare media directories, turn the
network off, or read from another storage:

```python
from andrep import AndRepRenderer, DefaultResolver

r = AndRepRenderer(
    "invoice", loader=loader,
    resolver=DefaultResolver(base_dir="templates/data",
                             roots={"media": "/srv/app/media"},
                             network=False),
)
```

A custom resolver is any object with `open(ref) -> (bytes, mime)` that raises
`andrep.ResourceError` when a resource cannot be read. When declaring roots, declare
directories whose content every template author may see: a directory holding the files of
all users or all tenants would bypass the application's permissions.

**Other types of data.** `andrep.register_adapter(cls, fn)` makes values of `cls` readable
by templates: `fn(value)` returns data — a string, a number, a dict of fields. It is
process-wide configuration, meant to be set once by an integration module:

```python
import enum, uuid
import andrep

andrep.register_adapter(uuid.UUID, str)
andrep.register_adapter(enum.Enum, lambda e: e.value)
```

The same mechanism serves ORM records: an adapter converting a record into a dict of the
fields a report may read lets the loop pass records as they are. Convert only the fields
reports need, and stop following relations after a level or two — relations often lead
back to where they started, and reading one can cost a database query.

**Loaders.** Custom loaders keep templates of a platform, a customer or a tenant in their
own storage; see the contract above.

**`trusted=True`** restores the behavior of earlier versions for the **expressions**: the
caller's globals and all locals are exposed as they are, `_r` is the live renderer, and
the expression checks are off. Use it only when the people who write the templates are
the people who run the code. Resource confinement does not depend on `trusted`: it is the
resolver you pass.

---

## What remains to the host

- **Exfiltration through external URLs.** A template can build the URL of an external
  image from report data, so that data reaches the host serving the image; in the same
  way it can signal when a report is printed. Removing this would mean giving up external
  resources: it is an accepted risk. Close it with `network=False` in the resolver —
  advisable for integrations and whenever templates come from third parties.
- **Overload.** An expression can consume memory or time. Run reports where this is
  bounded: a separate worker or process, a timeout, a memory limit.
- **HTML inserted into another page.** The CSP protects the generated HTML when it is
  served as a document of its own. If you insert it into another page (e.g. with
  `innerHTML`), sanitize it or isolate it, for example in a sandboxed `<iframe>`.

---

## Compatibility

Changes for templates and loops written for earlier versions:

- calls to methods of `_r` do not work — keep the value in an attribute;
- a template reading a local variable that is not data shows a marker — pass data, or
  register an adapter;
- `r["key"] = value` raises `TypeError` if the value is not data;
- `r.globals` holds functions: templates cannot read attributes of registered objects —
  put values in the workspace;
- absolute paths in `load` / `img` are refused — use `base_dir` or a named root;
- images are embedded as `data:` URLs: the HTML is self-contained and larger;
- `url(...)` in `cssExtra` is not loaded;
- `trusted=True` restores the previous behavior of expressions.
