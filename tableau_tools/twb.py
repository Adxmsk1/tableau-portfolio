"""Writes Tableau .twb files from Python - CSV sources, sheets and a fixed-size dashboard."""
from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def run_text(s) -> str:
    return esc(s).replace("\n", "&#10;")


@dataclass
class Datasource:
    key: str
    csv: Path
    caption: str = ""
    calcs: dict = field(default_factory=dict)      # name -> (formula, datatype, role, type)
    colors: dict = field(default_factory=dict)     # '[none:col:nk]' -> {value: hex}
    roles: dict = field(default_factory=dict)
    formats: dict = field(default_factory=dict)    # col -> number format, e.g. 'p0%'
    ramps: dict = field(default_factory=dict)      # '[sum:col:qk]' -> built-in palette name

    @staticmethod
    def ramp_xml(field_ref, ramp):
        # hand-written <color-palette> ramps get ignored, named palettes work
        return f"<encoding attr='color' field='{esc(field_ref)}' palette='{esc(ramp)}' type='interpolated' />"

    @property
    def name(self):
        return f"federated.{self.key}"

    def columns(self):
        df = pd.read_csv(self.csv, nrows=2000)
        out = []
        for c in df.columns:
            s = df[c]
            if pd.api.types.is_bool_dtype(s):
                dt = "boolean"
            elif pd.api.types.is_integer_dtype(s):
                dt = "integer"
            elif pd.api.types.is_float_dtype(s):
                dt = "real"
            elif c.lower() in ("date",) or c.lower().endswith("_date"):
                dt = "date"
            else:
                dt = "string"
            out.append((c, dt))
        return out

    def default_role(self, col, dt):
        if col in self.roles:
            return self.roles[col]
        if dt in ("integer", "real") and col not in ("season", "year", "rank", "month"):
            return ("measure", "quantitative")
        if col in ("season", "year", "month", "rank"):
            return ("dimension", "ordinal")
        if dt == "date":
            return ("dimension", "ordinal")
        return ("dimension", "nominal")

    def xml(self):
        cols = self.columns()
        p = self.csv.resolve()
        rel_cols = "".join(f"<column datatype='{dt}' name='{esc(c)}' ordinal='{i}' />" for i, (c, dt) in enumerate(cols))
        col_defs = []
        for c, dt in cols:
            role, typ = self.default_role(c, dt)
            fmt = f" default-format='{esc(self.formats[c])}'" if c in self.formats else ""
            col_defs.append(f"<column caption='{esc(c.replace('_', ' ').title())}' datatype='{dt}'{fmt} name='[{esc(c)}]' role='{role}' type='{typ}' />")
        for n, (formula, dt, role, typ) in self.calcs.items():
            col_defs.append(f"<column caption='{esc(n)}' datatype='{dt}' name='[{esc(n)}]' role='{role}' type='{typ}'>"
                            f"<calculation class='tableau' formula='{esc(formula)}' /></column>")
        style = ""
        # colours only stick if the field is also declared here, not just on the sheet
        for fld in list(self.colors) + list(self.ramps):
            m = re.match(r"\[(\w+):(.+):(\w+)\]$", fld)
            if m:
                agg, col, kind = m.groups()
                t = {"nk": "nominal", "ok": "ordinal", "qk": "quantitative"}[kind]
                col_defs.append(f"<column-instance column='[{esc(col)}]' derivation='{_DERIV[agg]}' name='{esc(fld)}' pivot='key' type='{t}' />")
        if self.colors or self.ramps:
            enc = ""
            for fld, mapping in self.colors.items():
                maps = "".join(f"<map to='{h}'><bucket>{esc(self._bucket(v))}</bucket></map>" for v, h in mapping.items())
                enc += f"<encoding attr='color' field='{esc(fld)}' type='palette'>{maps}</encoding>"
            for fld, ramp in self.ramps.items():
                enc += self.ramp_xml(fld, ramp)
            style = f"<style><style-rule element='mark'>{enc}</style-rule></style>"
        return (
            f"<datasource caption='{esc(self.caption or self.key)}' inline='true' name='{self.name}' version='18.1'>"
            f"<connection class='federated'><named-connections>"
            f"<named-connection caption='{esc(p.stem)}' name='textscan.{self.key}'>"
            f"<connection class='textscan' directory='{esc(p.parent.as_posix())}' filename='{esc(p.name)}' password='' server='' />"
            f"</named-connection></named-connections>"
            f"<relation connection='textscan.{self.key}' name='{esc(p.name)}' table='[{esc(p.stem)}#csv]' type='table'>"
            f"<columns character-set='UTF-8' header='yes' locale='en_GB' separator=','>{rel_cols}</columns></relation>"
            f"</connection><aliases enabled='yes' />{''.join(col_defs)}{style}</datasource>"
        )

    @staticmethod
    def _bucket(v):
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, (int, float)):
            return str(v)
        return f'"{v}"'


class Parameters:
    """List-of-strings parameters, used in formulas as [Parameters].[name]."""
    name = "Parameters"
    current = None

    def __init__(self, params: dict, defaults: dict | None = None):
        self.params, self.defaults = params, defaults or {}
        Parameters.current = self

    def ref(self, pname):
        return f"[Parameters].[{pname}]"

    def dependencies(self, formulas):
        used = [n for n in self.params if any(f"[Parameters].[{n}]" in fm for fm in formulas)]
        return f"<datasource-dependencies datasource='Parameters'>{self._columns(used)}</datasource-dependencies>" if used else ""

    def xml(self):
        return f"<datasource hasconnection='false' inline='true' name='Parameters' version='18.1'><aliases enabled='yes' />{self._columns(self.params)}</datasource>"

    def _columns(self, names):
        cols = ""
        for n in names:
            members = self.params[n]
            d = self.defaults.get(n, members[0])
            mem = "".join(f"<member value='{esc(chr(34) + m + chr(34))}' />" for m in members)
            cols += (f"<column caption='{esc(n)}' datatype='string' name='[{esc(n)}]' param-domain-type='list' role='measure' "
                     f"type='nominal' value='{esc(chr(34) + d + chr(34))}'><calculation class='tableau' formula='{esc(chr(34) + d + chr(34))}' />"
                     f"<members>{mem}</members></column>")
        return cols


def bool_filter(fld):
    return (fld, "<filter class='categorical' column='{REF}'><groupfilter function='member' level='[" + f"{fld[0]}:{esc(fld[1])}:{fld[2]}" +
            "]' member='true' user:ui-domain='database' user:ui-enumeration='inclusive' user:ui-marker='enumerate' /></filter>")


def member_filter(fld, value):
    v = f"&quot;{esc(value)}&quot;" if isinstance(value, str) else str(value)
    return (fld, "<filter class='categorical' column='{REF}'><groupfilter function='member' level='[" + f"{fld[0]}:{esc(fld[1])}:{fld[2]}" +
            f"]' member='{v}' user:ui-domain='database' user:ui-enumeration='inclusive' user:ui-marker='enumerate' /></filter>")


def theme_rules(bg, fg, muted, font="Tableau Book", size=9, grid=None, hide_axis_titles=(), hide_value_axis=False, free_axes=(),
                fixed_axes=()):
    # fixed_axes = [(field ref, min, max)]
    r = [f"<style-rule element='table'><format attr='background-color' value='{bg}' /></style-rule>",
         f"<style-rule element='worksheet'><format attr='font-family' value='{font}' /><format attr='color' value='{fg}' />"
         "<format attr='display-field-labels' scope='cols' value='false' /><format attr='display-field-labels' scope='rows' value='false' /></style-rule>",
         "<style-rule element='axis'>"
         + "".join(f"<encoding attr='space' class='0' field='{esc(f)}' field-type='quantitative' include-zero='false' scope='rows' type='space' />" for f in free_axes)
         + "".join(f"<encoding attr='space' class='0' field='{esc(f)}' field-type='quantitative' max='{hi}' min='{lo}' range-type='fixed' "
                   f"scope='rows' type='space' />" for f, lo, hi in fixed_axes)
         + f"<format attr='color' value='{muted}' /><format attr='font-size' value='{size}' />"
         + "".join(f"<format attr='title' class='0' field='{esc(f)}' scope='{s}' value='' />" for f, s in hide_axis_titles)
         + "</style-rule>",
         f"<style-rule element='header'><format attr='color' value='{muted}' /><format attr='font-size' value='{size}' /></style-rule>",
         "<style-rule element='zeroline'><format attr='line-visibility' value='off' /></style-rule>",
         "<style-rule element='dropline'><format attr='line-visibility' value='off' /></style-rule>",
         ]
    if grid:
        r.append(f"<style-rule element='gridline'><format attr='line-visibility' value='on' /><format attr='stroke-color' value='{grid}' /></style-rule>")
    else:
        r.append("<style-rule element='gridline'><format attr='line-visibility' value='off' /></style-rule>")
    r.append(f"<style-rule element='pane'><format attr='border-color' value='{bg}' /></style-rule>")
    return r


_DERIV = {"sum": "Sum", "avg": "Avg", "min": "Min", "max": "Max", "cnt": "Count", "ctd": "CountD", "none": "None",
          "attr": "Attribute", "med": "Median"}


def f(agg: str, col: str, kind: str = "") -> tuple:
    if not kind:
        kind = "qk" if agg != "none" else "nk"
    return (agg, col, kind)


class Sheet:
    def __init__(self, name, ds: Datasource, mark="Bar"):
        self.name, self.ds, self.mark = name, ds, mark
        self.rows, self.cols = [], []
        self.enc = {}            # color/size/text/detail/tooltip/path -> [fields]
        self.filters = []
        self.sort = None         # (field, by_field, direction)
        self.style_rules = []
        self.tooltip = None
        self.mark_color = None
        self.mark_size = None
        self.title = None
        self.label_show = False
        self.label = None
        self.uses_params = False
        self.label_cull = False

    def ref(self, fld):
        agg, col, kind = fld
        return f"[{self.ds.name}].[{agg}:{col}:{kind}]"

    def _instances(self):
        used = list(self.rows) + list(self.cols) + [x for v in self.enc.values() for x in v]
        if self.sort:
            used += [self.sort[0], self.sort[1]]
        used += [x[0] for x in self.filters if isinstance(x, tuple)]
        seen, out = set(), []
        for agg, col, kind in used:
            key = (agg, col, kind)
            if key in seen:
                continue
            seen.add(key)
            out.append(key)
        return out

    def xml(self):
        cols = {c: dt for c, dt in self.ds.columns()}
        deps, done, formulas = [], set(), []

        def base_col(col):
            role, typ = self.ds.default_role(col, cols[col])
            deps.append(f"<column datatype='{cols[col]}' name='[{esc(col)}]' role='{role}' type='{typ}' />")
            done.add(col)

        for agg, col, kind in self._instances():
            if col not in done:
                if col in cols:
                    base_col(col)
                else:
                    formula, dt, role, typ = self.ds.calcs[col]
                    formulas.append(formula)
                    for ref in re.findall(r"(?<!\.)\[([^\]]+)\](?!\.)", formula):
                        if ref in cols and ref not in done:
                            base_col(ref)
                    deps.append(f"<column caption='{esc(col)}' datatype='{dt}' name='[{esc(col)}]' role='{role}' type='{typ}'>"
                                f"<calculation class='tableau' formula='{esc(formula)}' /></column>")
                done.add(col)
            t = {"nk": "nominal", "ok": "ordinal", "qk": "quantitative"}[kind]
            deps.append(f"<column-instance column='[{esc(col)}]' derivation='{_DERIV[agg]}' name='[{agg}:{esc(col)}:{kind}]' pivot='key' type='{t}' />")
        filters = ""
        for fl in self.filters:
            if isinstance(fl, tuple):
                fld, xml = fl
                filters += xml.replace("{REF}", esc(self.ref(fld)))
            else:
                filters += fl
        sort = ""
        if self.sort:
            fld, by, d = self.sort
            sort = f"<sort class='computed' column='{esc(self.ref(fld))}' direction='{d}' using='{esc(self.ref(by))}' />"
        enc = ""
        for k, flds in self.enc.items():
            tag = {"detail": "lod"}.get(k, k)
            for fld in flds:
                enc += f"<{tag} column='{esc(self.ref(fld))}' />"
        for fld in self.enc.get("color", []):
            mapping = self.ds.colors.get(f"[{fld[0]}:{fld[1]}:{fld[2]}]")
            if mapping:
                maps = "".join(f"<map to='{h}'><bucket>{esc(self.ds._bucket(v))}</bucket></map>" for v, h in mapping.items())
                self.style_rules = list(self.style_rules) + [f"<style-rule element='mark'><encoding attr='color' field='{esc(self.ref(fld))}' type='palette'>{maps}</encoding></style-rule>"]
            ramp = self.ds.ramps.get(f"[{fld[0]}:{fld[1]}:{fld[2]}]")
            if ramp:
                self.style_rules = list(self.style_rules) + [f"<style-rule element='mark'>{self.ds.ramp_xml(self.ref(fld), ramp)}</style-rule>"]
        mark_style = ""
        fmts = []
        if self.mark_color:
            fmts.append(f"<format attr='mark-color' value='{self.mark_color}' />")
        if self.mark_size is not None:
            fmts.append(f"<format attr='size' value='{self.mark_size}' />")
        if self.label_show or self.label:
            fmts.append("<format attr='mark-labels-show' value='true' />")
            fmts.append(f"<format attr='mark-labels-cull' value='{'true' if self.label_cull else 'false'}' />")
        if fmts:
            mark_style = f"<style><style-rule element='mark'>{''.join(fmts)}</style-rule></style>"

        def field_run(ref, a, label):
            return f"<run{a}>{esc('<' + ref + '>')}</run>"

        def runs_xml(items, label=False):
            runs = ""
            for item in items:
                if isinstance(item, tuple) and len(item) == 3 and item[0] in _DERIV:
                    runs += field_run(self.ref(item), " bold='true'", label)
                elif isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], tuple):
                    a = "".join(f" {k}='{esc(v)}'" for k, v in item[1].items())
                    runs += field_run(self.ref(item[0]), a, label)
                else:
                    text, attrs = (item, {}) if isinstance(item, str) else item
                    a = "".join(f" {k}='{esc(v)}'" for k, v in attrs.items())
                    # line breaks need their own 'Æ\n' run, otherwise the Æ is printed
                    parts = text.split("\n")
                    for i, part in enumerate(parts):
                        if part:
                            runs += f"<run{a}>{esc(part)}</run>"
                        if i < len(parts) - 1:
                            runs += f"<run{a}>Æ&#10;</run>"
            return runs

        tip = ""
        if self.tooltip:
            tip = f"<customized-tooltip><formatted-text>{runs_xml(self.tooltip)}</formatted-text></customized-tooltip>"
        if self.label:
            tip += f"<customized-label><formatted-text>{runs_xml(self.label, label=True)}</formatted-text></customized-label>"
        title = ""
        if self.title is not None:
            title = f"<layout-options><title><formatted-text><run>{esc(self.title)}</run></formatted-text></title></layout-options>"
        rows = " / ".join(self.ref(x) for x in self.rows) if len(self.rows) > 1 else (self.ref(self.rows[0]) if self.rows else "")
        cols_ = " / ".join(self.ref(x) for x in self.cols) if len(self.cols) > 1 else (self.ref(self.cols[0]) if self.cols else "")
        if len(self.rows) > 1:
            rows = "(" + rows + ")"
        if len(self.cols) > 1:
            cols_ = "(" + cols_ + ")"
        return (
            f"<worksheet name='{esc(self.name)}'>{title}<table><view>"
            # don't add a Parameters <datasource> here - 2026.2 rejects the sheet if you do
            f"<datasources><datasource caption='{esc(self.ds.caption or self.ds.key)}' name='{self.ds.name}' /></datasources>"
            f"{Parameters.current.dependencies(formulas) if self.uses_params and Parameters.current else ''}"
            f"<datasource-dependencies datasource='{self.ds.name}'>{''.join(deps)}</datasource-dependencies>"
            f"{filters}{sort}<aggregation value='true' /></view>"
            f"<style>{''.join(self.style_rules)}</style>"
            f"<panes><pane selection-relaxation-option='selection-relaxation-allow'><view><breakdown value='auto' /></view>"
            f"<mark class='{self.mark}' /><encodings>{enc}</encodings>{tip}{mark_style}</pane></panes>"
            f"<rows>{esc(rows)}</rows><cols>{esc(cols_)}</cols></table></worksheet>"
        )


class Dashboard:
    def __init__(self, name, width, height, bg="#FFFFFF"):
        self.name, self.w, self.h, self.bg = name, width, height, bg
        self.zones = []
        self._id = 10

    def _box(self, x, y, w, h):
        k = 100000
        return f"x='{round(x / self.w * k)}' y='{round(y / self.h * k)}' w='{round(w / self.w * k)}' h='{round(h / self.h * k)}'"

    def _style(self, bg=None, border=None, margin=0, padding=None):
        f = []
        if bg:
            f.append(f"<format attr='background-color' value='{bg}' />")
        if border:
            f += [f"<format attr='border-color' value='{border}' />", "<format attr='border-style' value='solid' />",
                  "<format attr='border-width' value='1' />"]
        else:
            f += ["<format attr='border-style' value='none' />", "<format attr='border-width' value='0' />"]
        f.append(f"<format attr='margin' value='{margin}' />")
        if padding is not None:
            f.append(f"<format attr='padding' value='{padding}' />")
        return f"<zone-style>{''.join(f)}</zone-style>"

    @property
    def sheet_names(self):
        return list(dict.fromkeys(re.findall(r"<zone [^>]*id='\d+' name='([^']+)' show-title='false'>", "".join(self.zones))))

    def sheet(self, sheet_name, x, y, w, h, bg=None, border=None, padding=None):
        self._id += 1
        self.zones.append(f"<zone {self._box(x, y, w, h)} id='{self._id}' name='{esc(sheet_name)}' show-title='false'>"
                          f"{self._style(bg, border, padding=padding)}</zone>")

    def text(self, runs, x, y, w, h, bg=None, border=None, padding=4, align="left", valign=None):
        self._id += 1
        r = ""
        # tableau drops whitespace-only runs, so tack bare newlines onto the run before
        merged = []
        for item in runs:
            text = item if isinstance(item, str) else item[0]
            if merged and text.strip() == "" and "\n" in text:
                prev = merged[-1]
                merged[-1] = (prev + text) if isinstance(prev, str) else (prev[0] + text, prev[1])
            else:
                merged.append(item)
        for item in merged:
            text, attrs = (item, {}) if isinstance(item, str) else item
            a = "".join(f" {k}='{esc(v)}'" for k, v in attrs.items())
            r += f"<run{a}>{run_text(text)}</run>"
        al = f" fontalignment='{ {'left': 0, 'center': 1, 'right': 2}[align] }'" if align != "left" else ""
        self.zones.append(f"<zone {self._box(x, y, w, h)} id='{self._id}' type-v2='text'>"
                          f"<formatted-text>{r.replace('<run', '<run' + al, 1) if al else r}</formatted-text>{self._style(bg, border, padding=padding)}</zone>")

    def blank(self, x, y, w, h, bg):
        self._id += 1
        self.zones.append(f"<zone {self._box(x, y, w, h)} id='{self._id}' type-v2='empty'>{self._style(bg)}</zone>")

    def image(self, path, x, y, w, h, fit=True):
        self._id += 1
        self.zones.append(f"<zone {self._box(x, y, w, h)} id='{self._id}' param='{esc(Path(path).as_posix())}' type-v2='bitmap' "
                          f"is-scaled='{1 if fit else 0}'>{self._style()}</zone>")

    def param_control(self, param_ref, x, y, w, h, mode="compact"):
        self._id += 1
        self.zones.append(f"<zone {self._box(x, y, w, h)} id='{self._id}' mode='{mode}' param='{esc(param_ref)}' "
                          f"type-v2='paramctrl'>{self._style()}</zone>")

    def legend(self, sheet_name, field_ref, x, y, w, h, horizontal=True):
        self._id += 1
        lay = " leg-item-layout='horz'" if horizontal else ""
        self.zones.append(f"<zone {self._box(x, y, w, h)} id='{self._id}'{lay} name='{esc(sheet_name)}' pane-specification-id='0' "
                          f"param='{esc(field_ref)}' show-title='false' type-v2='color'>{self._style()}</zone>")

    def filter(self, sheet_name, field_ref, x, y, w, h, mode="dropdown", title=None):
        self._id += 1
        self.zones.append(f"<zone {self._box(x, y, w, h)} id='{self._id}' mode='{mode}' name='{esc(sheet_name)}' param='{esc(field_ref)}' "
                          f"type-v2='filter'>{self._style()}</zone>")

    def xml(self):
        return (
            f"<dashboard name='{esc(self.name)}'><style><style-rule element='table'><format attr='background-color' value='{self.bg}' /></style-rule></style><size maxheight='{self.h}' maxwidth='{self.w}' minheight='{self.h}' minwidth='{self.w}' />"
            f"<datasources />"
            f"<zones><zone h='100000' id='2' type-v2='layout-basic' w='100000' x='0' y='0'>{''.join(self.zones)}"
            f"{self._style(self.bg)}</zone></zones></dashboard>"
        )


def workbook(datasources, sheets, dashboards, path: Path, font="Tableau Book"):
    xml = (
        "<?xml version='1.0' encoding='utf-8' ?>\n"
        "<workbook source-build='2026.2.0' source-platform='win' version='18.1' xmlns:user='http://www.tableausoftware.com/xml/user'>"
        "<preferences><preference name='ui.encoding.shelf.height' value='24' /><preference name='ui.shelf.height' value='26' /></preferences>"
        f"<style><style-rule element='all'><format attr='font-family' value='{font}' /></style-rule></style>"
        f"<datasources>{''.join(d.xml() for d in datasources)}</datasources>"
        f"<worksheets>{''.join(s.xml() for s in sheets)}</worksheets>"
        + (f"<dashboards>{''.join(d.xml() for d in dashboards)}</dashboards>" if dashboards else "") +
        "<windows>"
        + "".join(f"<window class='worksheet' hidden='true' maximized='true' name='{esc(s.name)}'><cards /></window>" for s in sheets)
        + "".join(f"<window class='dashboard' maximized='true' name='{esc(d.name)}'><viewpoints>"
                  + "".join(f"<viewpoint name='{esc(n)}'><zoom type='entire-view' /></viewpoint>" for n in d.sheet_names)
                  + "</viewpoints><active id='-1' /></window>" for d in dashboards)
        + "</windows></workbook>"
    )
    path.write_text(xml, encoding="utf-8")
    return path
