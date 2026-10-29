"""Six report dashboards (KPI cards, side panel, titled chart cards) as 16:9 PNGs and one PDF, drawn from outputs/.

    python run_all.py --report     # redraw from the cached outputs in seconds
"""
import json
import textwrap
from collections import Counter

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch, Polygon

from atp import config as C

# shop-floor palette, shared with the app: steel blue and safety amber on a dark band
BG, SHEET, EDGE, INK, MUTED, CHIP = "#E4E9EE", "#FFFFFF", "#D6DDE3", "#14202B", "#6F7C87", "#E8ECF0"
BAND, BAND2, STEEL, SKY, AMBER, GREEN, RED = "#152A3D", "#1E3A52", "#1E4D74", "#8DB3D3", "#E5A21A", "#1B7444", "#A8281F"
ICON, DISPLAY = "Segoe MDL2 Assets", "Bahnschrift"
plt.rcParams.update({"font.family": "Segoe UI", "font.size": 9, "text.color": INK, "text.parse_math": False})
I = {"people": "", "work": "", "pin": "", "car": "", "edu": "", "money": "",
     "check": "", "warn": "", "chart": "", "factory": "", "gear": "", "swap": "",
     "up": "", "down": "", "layers": "", "list": "", "history": "", "chevron": ""}
PAGES = [("Overview", "chart", "Both plants"), ("Re-employment plan", "people", "12-month placement"),
         ("Assemblers' options", "swap", "70% of the workforce"), ("Commute & training", "car", "Rush-hour drive"),
         ("Product fit", "factory", "10 candidate products"), ("Product trade-offs", "gear", "Pay, staff, retraining")]
FILES = ["P1_overview", "P2_reemployment_plan", "P3_assemblers_options", "P4_commute_and_training",
         "P5_new_products_fit", "P6_new_products_tradeoffs"]
R1 = [(0.135, 0.455, 0.274, 0.335), (0.4205, 0.455, 0.274, 0.335), (0.706, 0.455, 0.284, 0.335)]
R2 = [(0.135, 0.045, 0.415, 0.335), (0.561, 0.045, 0.429, 0.335)]
R3 = [(x, 0.045, w, h) for x, _, w, h in R1]
PN = {"brampton": "Brampton", "cami": "Ingersoll"}
PC = {"brampton": STEEL, "cami": AMBER}
NOTE = "Independent analysis of public data. Not produced by or affiliated with Stellantis, General Motors, Unifor or any government."


# ---------------------------------------------------------------------------------------- page furniture
def rbox(fig, x, y, w, h, fc=SHEET, ec=EDGE, r=0.012, shadow=True):
    ax = fig.add_axes([x, y, w, h], zorder=-2)
    ax.axis("off")
    asp = (w * fig.get_figwidth()) / (h * fig.get_figheight())
    if shadow:
        ax.add_patch(FancyBboxPatch((0.004, -0.012), 1, 1, boxstyle=f"round,pad=0,rounding_size={r*3}", mutation_aspect=asp,
                                    transform=ax.transAxes, fc="#C7D0D8", ec="none", alpha=0.55, clip_on=False))
    ax.add_patch(FancyBboxPatch((0, 0), 1, 1, boxstyle=f"round,pad=0,rounding_size={r*3}", mutation_aspect=asp,
                                transform=ax.transAxes, fc=fc, ec=ec, lw=0.9, clip_on=False))
    return ax


def hazard(fig, x, y, w, h, n=16):
    """Amber-and-black safety stripes."""
    ax = fig.add_axes([x, y, w, h], zorder=-1)
    ax.axis("off")
    ax.set_xlim(0, n)
    ax.set_ylim(0, 1)
    for i in range(n):
        ax.add_patch(Polygon([(i, 0), (i + 0.5, 0), (i + 1.1, 1), (i + 0.6, 1)], closed=True, fc=AMBER, ec="none"))


def frame(page_no, kpis, source):
    fig = plt.figure(figsize=(16, 9), facecolor=BG)
    title, _, scope = PAGES[page_no - 1]
    rbox(fig, 0.008, 0.02, 0.118, 0.96, fc=BAND, ec=BAND, shadow=False)
    hazard(fig, 0.012, 0.952, 0.110, 0.020)
    fig.text(0.067, 0.898, I["work"], family=ICON, fontsize=28, color=AMBER, ha="center")
    fig.text(0.067, 0.862, "NEXT SHIFT", fontsize=15, family=DISPLAY, color="#EEF3F7", ha="center")
    fig.text(0.067, 0.843, "Autoworker transition platform", fontsize=7.4, color="#A9BCCB", ha="center")
    fig.text(0.067, 0.810, f"Page {page_no} of {len(PAGES)}", fontsize=7.5, color="#A9BCCB", ha="center")
    fig.text(0.067, 0.790, title.upper(), fontsize=10, family=DISPLAY, color=AMBER, ha="center")
    boxes = [("Plants", "Brampton · Ingersoll"), ("Workers", "3,959 displaced"), ("Postings", "Job Bank, Apr–Sep 2026"), ("Scope", scope)]
    for i, (lab, val) in enumerate(boxes):
        y = 0.70 - i * 0.085
        rbox(fig, 0.016, y, 0.102, 0.072, fc=BAND2, ec="#2C4D69", shadow=False)
        fig.text(0.024, y + 0.050, lab, fontsize=8, weight="semibold", color="#EEF3F7")
        fig.text(0.024, y + 0.018, val, fontsize=7.2, color="#A9BCCB")
        fig.text(0.108, y + 0.050, I["chevron"], family=ICON, fontsize=7, color="#7F95A8", ha="center")
    for i, (_, ic, _) in enumerate(PAGES):
        cx, cy = (0.040, 0.093)[i % 2], 0.335 - (i // 2) * 0.078
        on = i == page_no - 1
        rbox(fig, cx - 0.021, cy - 0.031, 0.042, 0.062, fc=AMBER if on else BAND2, ec=AMBER if on else "#2C4D69", r=0.03, shadow=False)
        fig.text(cx, cy + 0.002, I[ic], family=ICON, fontsize=15, color=BAND if on else "#A9BCCB", ha="center", va="center")
        fig.text(cx, cy - 0.022, str(i + 1), fontsize=6.2, color=BAND if on else "#7F95A8", ha="center")
    fig.text(0.067, 0.070, "Analysis and design by", fontsize=6.6, color="#A9BCCB", ha="center")
    fig.text(0.067, 0.050, "Osman Zakaria, PMP", fontsize=9.2, family=DISPLAY, color=AMBER, ha="center")
    fig.text(0.067, 0.031, "© 2026", fontsize=6.6, color="#A9BCCB", ha="center")
    x0, w, gap = 0.135, 0.1345, 0.0076
    for i, (ic, val, lab) in enumerate(kpis):
        x = x0 + i * (w + gap)
        rbox(fig, x, 0.875, w, 0.105, r=0.03)
        fig.add_artist(plt.Rectangle((x + 0.004, 0.875), w - 0.008, 0.006, color=AMBER, transform=fig.transFigure, zorder=3))
        fig.text(x + 0.020, 0.940, I[ic], family=ICON, fontsize=18, color=STEEL, ha="center", va="center")
        fig.text(x + 0.039, 0.939, val, fontsize=21, family=DISPLAY, color=BAND, va="center")
        fig.text(x + w / 2, 0.898, lab, fontsize=7.4, weight="semibold", color=MUTED, ha="center", va="center")
    fig.text(0.135, 0.008, f"{source} {NOTE}", fontsize=6.6, color=MUTED)
    return fig


def chart(fig, x, y, w, h, title, pl=0.0, pb=0.0):
    rbox(fig, x, y + h + 0.010, w, 0.040, fc=BAND, ec=BAND, r=0.006)
    fig.text(x + w / 2, y + h + 0.030, title, fontsize=8.8, weight="bold", color="#EEF3F7", ha="center", va="center")
    rbox(fig, x, y, w, h, r=0.008)
    ax = fig.add_axes([x + 0.012 + pl, y + 0.045 + pb, w - 0.024 - pl, h - 0.075 - pb], zorder=2)
    ax.patch.set_alpha(0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0, labelsize=7.6, colors=INK)
    ax.set_yticks([])
    return ax


# ---------------------------------------------------------------------------------------- chart kinds
def chip(ax, x, y, text, fs=7.2, horizontal=False):
    off = (6, 0) if horizontal else (0, 6)
    ax.annotate(text, (x, y), xytext=off, textcoords="offset points", ha="left" if horizontal else "center",
                va="center" if horizontal else "bottom", fontsize=fs, bbox=dict(boxstyle="round,pad=0.28,rounding_size=0.5", fc=CHIP, ec="none"))


def short(labels, n=12):
    return ["\n".join(textwrap.wrap(str(l), n, break_long_words=False)) for l in labels]


def legend(ax, names, colors):
    h = [plt.Line2D([], [], marker="o", ls="", ms=6, color=c, label=n) for n, c in zip(names, colors)]
    ax.legend(handles=h, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=len(names), frameon=False,
              fontsize=7.4, handletextpad=0.3, columnspacing=1.0, borderaxespad=0.2)


def vbar(ax, labels, vals, fmt="{:,.0f}", colors=STEEL, wrap=11, fs=7.4):
    xs = range(len(vals))
    ax.bar(xs, vals, color=colors, width=0.62)
    for x, v in zip(xs, vals):
        chip(ax, x, v, fmt.format(v))
    ax.set_ylim(0, max(vals) * 1.25)
    ax.set_xticks(list(xs))
    ax.set_xticklabels(short(labels, wrap), fontsize=fs)


def hbar(ax, labels, vals, fmt="{:,.0f}", colors=STEEL, xmax=None, fs=7.4):
    ys = list(range(len(vals)))[::-1]
    ax.barh(ys, vals, color=colors, height=0.62)
    for y, v in zip(ys, vals):
        chip(ax, v, y, fmt.format(v), fs=6.9, horizontal=True)
    ax.set_yticks(ys)
    ax.set_yticklabels(labels, fontsize=fs)
    ax.set_xticks([])
    ax.set_xlim(0, (xmax or max(vals)) * 1.22)


def grouped(ax, cats, series, fmt="{:,.0f}", wrap=11, fs=7.4):
    k = len(series)
    w = 0.8 / k
    allv = []
    for j, (_, vals, color) in enumerate(series):
        xs = [i - 0.4 + w * (j + 0.5) for i in range(len(cats))]
        ax.bar(xs, vals, width=w * 0.9, color=color)
        for x, v in zip(xs, vals):
            chip(ax, x, v, fmt.format(v), fs=6.6)
        allv += vals
    ax.set_ylim(0, max(allv) * 1.3)
    ax.set_xticks(range(len(cats)))
    ax.set_xticklabels(short(cats, wrap), fontsize=fs)
    legend(ax, [s[0] for s in series], [s[2] for s in series])


def stack_h(ax, labels, parts, fmt="{:.0%}"):
    """100% horizontal stacked bars: parts is [(name, values, color)]."""
    ys = list(range(len(labels)))[::-1]
    left = np.zeros(len(labels))
    for name, vals, col in parts:
        vals = np.asarray(vals, dtype=float)
        ax.barh(ys, vals, left=left, color=col, height=0.62, edgecolor=SHEET, lw=0.8)
        for y, l, v in zip(ys, left, vals):
            if v >= 0.06:
                ax.text(l + v / 2, y, fmt.format(v), ha="center", va="center", fontsize=7, color="white" if col != SKY else INK, weight="semibold")
        left += vals
    ax.set_yticks(ys)
    ax.set_yticklabels(labels, fontsize=7.4)
    ax.set_xlim(0, 1)
    ax.set_xticks([])
    legend(ax, [p[0] for p in parts], [p[2] for p in parts])


def clip(s, n):
    s = str(s)
    return s if len(s) <= n else s[: n - 1].rstrip(" ,") + "…"


SHORT = {"Motor vehicle assemblers, inspectors and testers": "Assemblers", "Material handlers": "Material handlers",
         "Construction millwrights and industrial mechanics": "Millwrights", "Industrial electricians": "Electricians",
         "Industrial painters, coaters and metal finishing process operators": "Painters", "Supervisors, motor vehicle assembling": "Supervisors",
         "Welders and related machine operators": "Welders", "Tool and die makers": "Tool and die",
         "Mechanical engineering technologists and technicians": "Mech. technologists", "Light duty cleaners": "Cleaners",
         "Automotive service technicians, truck and bus mechanics and mechanical repairers": "Auto technicians",
         "Steamfitters, pipefitters and sprinkler system installers": "Pipefitters"}


# ---------------------------------------------------------------------------------------- the pages
def load():
    o = C.OUT
    return {"s": json.loads((o / "summary.json").read_text()), "plan": pd.read_csv(o / "reemployment_plan.csv"),
            "tr": pd.read_csv(o / "transitions.csv"), "rp": pd.read_csv(o / "repurposing.csv"),
            "fl": pd.read_csv(o / "repurposing_flows.csv"), "tp": pd.read_csv(o / "training_programs_located.csv")}


def build(out_dir=None):
    out_dir = out_dir or C.OUT / "dashboards"
    d = load()
    S, plan, tr, rp, fl, tp = d["s"], d["plan"], d["tr"], d["rp"], d["fl"], d["tp"]
    B, K = S["brampton"], S["cami"]
    plants = ["brampton", "cami"]
    src = (f"Sources: ESDC Job Bank postings {S['postings']['window'][0]} to {S['postings']['window'][1]} ({S['postings']['rows']:,} Ontario); "
           "OaSIS 2022 skills; ESDC Wages 2025; StatCan 2021 road network.")
    figs = []
    plan["short"] = plan.origin_name.map(SHORT).fillna(plan.origin_name)

    # 1 Overview ------------------------------------------------------------------------------------
    fig = frame(1, [("people", f"{B['displaced'] + K['displaced']:,}", "Workers displaced"), ("list", f"{S['postings']['rows'] / 1e3:.1f}K", "Ontario job postings"),
                    ("check", f"{B['placed_12m'] / B['displaced']:.0%}", "Brampton placed in 12 months"), ("check", f"{K['placed_12m'] / K['displaced']:.0%}", "Ingersoll placed in 12 months"),
                    ("money", f"{B['pay_kept_placed']:.0%}", "Pay kept, Brampton placed"), ("money", f"{K['pay_kept_placed']:.0%}", "Pay kept, Ingersoll placed")],
                src + " Placement uses default assumptions: match 75+, 60%+ of pay, training up to 6 months, 10% of openings won.")
    grouped(chart(fig, *R1[0], "Displaced, placed in 12 months and still to place (workers)"), ["Displaced", "Placed", "Still to place"],
            [(PN[p], [S[p]["displaced"], S[p]["placed_12m"], S[p]["not_placed"]], PC[p]) for p in plants])
    bands = [str(b) for b in C.COMMUTE_BANDS]
    grouped(chart(fig, *R1[1], "Job postings within a rush-hour drive (Apr–Sep 2026)"), [f"{b} min" for b in bands],
            [(PN[p], [S[p]["postings_within"][b] for b in bands], PC[p]) for p in plants])
    per = [S[p]["postings_within"]["60"] / S[p]["displaced"] for p in plants]
    vbar(chart(fig, *R1[2], "Postings within 60 minutes per displaced worker"), [PN[p] for p in plants], per, fmt="{:.1f}",
         colors=[PC[p] for p in plants], wrap=12)
    mix = plan.groupby(["plant", "short"]).workers.sum().unstack(0).fillna(0)
    mix = mix.loc[mix.sum(axis=1).sort_values(ascending=False).index]
    ax = chart(fig, *R2[0], "The workforce: estimated mix by plant job (workers)", pl=0.07)
    hbar(ax, list(mix.index), list(mix.sum(axis=1)), colors=[STEEL if i == 0 else SKY for i in range(len(mix))])
    ax.text(0.98, 0.04, f"Assemblers are {mix.iloc[0].sum() / mix.values.sum():.0%} of both plants.\nMix is estimated; the seniority list would replace it.",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=7.2, color=MUTED)
    pr = (plan[plan.target.notna()].groupby(["plant", "short"]).workers.sum() / plan.groupby(["plant", "short"]).workers.sum()).unstack(0).fillna(0)
    pr = pr.loc[mix.index]
    grouped(chart(fig, *R2[1], "Share placed within 12 months, by plant job (%)"), list(pr.index),
            [(PN[p], list((100 * pr[p]).round()), PC[p]) for p in plants], fmt="{:.0f}", wrap=9, fs=6.8)
    figs.append(fig)

    # 2 Re-employment plan --------------------------------------------------------------------------
    placed = plan[plan.target.notna()]
    asm = plan[plan.short == "Assemblers"]
    asm_rate = {p: asm[(asm.plant == p) & asm.target.notna()].workers.sum() / asm[asm.plant == p].workers.sum() for p in plants}
    trade_rate = plan[~plan.short.isin(["Assemblers", "Supervisors"])]
    trade_rate = trade_rate[trade_rate.target.notna()].workers.sum() / trade_rate.workers.sum()
    fig = frame(2, [("people", f"{B['not_placed'] + K['not_placed']:,}", "Workers still to place"), ("check", f"{trade_rate:.0%}", "Trades and handlers placed"),
                    ("warn", f"{asm_rate['brampton']:.0%}", "Brampton assemblers placed"), ("warn", f"{asm_rate['cami']:.0%}", "Ingersoll assemblers placed"),
                    ("car", f"{placed[placed.target_name == 'Transport truck drivers'].workers.sum():,}", "Placed as truck drivers"),
                    ("history", f"{(placed.workers * placed.train_months).sum() / placed.workers.sum():.1f} mo", "Average training, placed")],
                src + " Placement starts with the plant jobs that have the fewest good options.")
    for slot, p in zip(R2, plants):
        top = pd.Series(S[p]["top_destinations"]).head(8)
        ax = chart(fig, *slot, f"{PN[p]}: where placed workers go (top 8 destinations, workers)", pl=0.13)
        hbar(ax, [clip(n, 44) for n in top.index], list(top.values), colors=PC[p])
    wr = placed.assign(band=pd.cut(placed.wage_ratio, [0, 0.6, 0.7, 0.8, 0.9, 1.0, 9], labels=["<60%", "60–70%", "70–80%", "80–90%", "90–100%", "100%+"]))
    wb = wr.groupby(["band", "plant"], observed=False).workers.sum().unstack(1).fillna(0)
    grouped(chart(fig, *R1[0], "Pay kept by placed workers (workers by share of plant pay)"), list(wb.index),
            [(PN[p], list(wb[p].astype(int)), PC[p]) for p in plants])
    tb = placed.assign(m=placed.train_months.round().clip(upper=6).astype(int)).groupby(["m", "plant"]).workers.sum().unstack(1).fillna(0)
    grouped(chart(fig, *R1[1], "Training before starting, placed workers (months)"), [f"{m} mo" if m < 6 else "6 mo" for m in tb.index],
            [(PN[p], list(tb[p].astype(int)), PC[p]) for p in plants])
    un = plan[plan.target.isna()].groupby(["plant", "short"]).workers.sum().unstack(0).fillna(0)
    grouped(chart(fig, *R1[2], "Still to place: the retraining and outreach target (workers)"), list(un.index),
            [(PN[p], list(un[p].astype(int)), PC[p]) for p in plants], wrap=12)
    figs.append(fig)

    # 3 Assemblers' options -------------------------------------------------------------------------
    a = tr[tr.origin_name == "Motor vehicle assemblers, inspectors and testers"]
    ab = a[a.plant == "brampton"]
    good = ab[(ab.match >= 75) & (ab.wage_ratio >= 0.6)]
    fig = frame(3, [("people", f"{int(mix.iloc[0].sum()):,}", "Assemblers across both plants"), ("list", f"{len(ab)}", "Occupations with match 60+"),
                    ("check", f"{len(good)}", "Match 75+ and 60%+ of pay"), ("car", f"{ab.set_index('target_name').loc['Transport truck drivers', 'vac_60']:.0f}", "Truck-driver postings/month, 60 min"),
                    ("money", f"{ab.set_index('target_name').loc['Transport truck drivers', 'wage_ratio']:.0%}", "Truck-driver pay vs assembly"),
                    ("edu", "1 mo", "Class A licence training")],
                src + " Openings are average postings per month within a 60-minute drive of Brampton. Match = 0.6 × readiness + 0.4 × relevance.")
    ax = chart(fig, *R2[0], "Brampton assemblers: skill match vs openings within 60 min (bubble = pay kept)", pl=0.035, pb=0.03)
    x, y = ab.match, ab.vac_60.clip(lower=0.5)
    cols = [GREEN if t <= 1 else AMBER if t <= 8 else RED for t in ab.train_months]
    ax.scatter(x, y, s=(ab.wage_ratio.clip(0.3, 1.3) * 90) ** 1.2, c=cols, alpha=0.65, edgecolors=SHEET, linewidths=0.6)
    ax.set_yscale("log")
    ax.set_xlabel("Skill match (0–100)", fontsize=7.6, color=MUTED); ax.set_ylabel("Postings per month (log)", fontsize=7.6, color=MUTED)
    ax.tick_params(labelsize=7, colors=MUTED)
    ax.set_yticks([1, 10, 100]); ax.set_yticklabels(["1", "10", "100"])
    ax.grid(color="#E8ECF0", lw=0.7); ax.set_axisbelow(True)
    for name, off in [("Transport truck drivers", (8, -10)), ("Welders and related machine operators", (8, 4)),
                      ("Mechanical assemblers and inspectors", (8, -2))]:
        r = ab[ab.target_name == name]
        if len(r):
            r = r.iloc[0]
            ax.annotate(clip(name, 26), (r.match, max(r.vac_60, 0.5)), xytext=off, textcoords="offset points", fontsize=6.9, color=INK,
                        arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6))
    legend(ax, ["Ready in a month", "Up to 8 months' training", "Longer training"], [GREEN, AMBER, RED])
    top = ab.sort_values("score", ascending=False).head(10)
    ax = chart(fig, *R2[1], "Brampton assemblers: the 10 best-ranked options (pay kept; training months)", pl=0.15)
    hbar(ax, [f"{clip(n, 40)} ({m:.0f} mo)" for n, m in zip(top.target_name, top.train_months)], list(100 * top.wage_ratio), fmt="{:.0f}%",
         colors=[GREEN if w >= 0.9 else AMBER if w >= 0.7 else RED for w in top.wage_ratio])
    bands_ = pd.cut(ab.match, [60, 70, 80, 90, 101], right=False, labels=["60–70", "70–80", "80–90", "90+"])
    pay_ = ab.groupby(bands_, observed=False).wage_ratio.median()
    vbar(chart(fig, *R1[0], "The trade-off: closer skill match, lower pay (median pay kept, %)"), [f"Match {b}" for b in pay_.index],
         list(100 * pay_.values), fmt="{:.0f}%", colors=STEEL, wrap=8)
    gaps = Counter(g.strip() for gs in ab.loc[ab.match >= 75, "top_gaps"].dropna() for g in gs.split(";"))
    gp = pd.Series(gaps).sort_values(ascending=False).head(6)
    ax = chart(fig, *R1[1], "Most common skill gaps for assemblers (options with match 75+)", pl=0.10)
    hbar(ax, [clip(g, 30) for g in gp.index], list(gp.values), colors=STEEL)
    ing = a[a.plant == "cami"]
    vac = {p: a[(a.plant == p) & (a.match >= 75)].vac_60.sum() for p in plants}
    vbar(chart(fig, *R1[2], "Good-fit postings per month within 60 min, per assembler"), [PN[p] for p in plants],
         [vac[p] / mix.loc["Assemblers", p] for p in plants], fmt="{:.2f}", colors=[PC[p] for p in plants], wrap=12)
    figs.append(fig)

    # 4 Commute and training ------------------------------------------------------------------------
    near = {p: tp[tp[f"min_{p}"] <= 75] for p in plants}
    fig = frame(4, [("edu", f"{len(tp)}", "Training programs listed"), ("pin", f"{len(near['brampton'])}", "Within 75 min of Brampton"),
                    ("pin", f"{len(near['cami'])}", "Within 75 min of Ingersoll"), ("history", f"{tp.months.median():.0f} mo", "Median program length"),
                    ("car", f"{B['postings_within']['30'] / K['postings_within']['30']:.0f}x", "Brampton vs Ingersoll, 30 min"),
                    ("car", f"{K['postings_within']['90'] / K['postings_within']['60']:.1f}x", "Ingersoll postings, 90 vs 60 min")],
                src + " Drive times on the 2021 road network with a rush-hour factor; programs curated from college and Ontario pages.")
    ax = chart(fig, *R1[0], "Postings reachable as the commute grows (thousands)", pb=0.02)
    xs = [int(b) for b in bands]
    for p in plants:
        ys = [S[p]["postings_within"][b] / 1e3 for b in bands]
        ax.plot(xs, ys, color=PC[p], lw=2.4, marker="o", ms=5)
        for x_, y_ in zip(xs, ys):
            chip(ax, x_, y_, f"{y_:.1f}K", fs=6.6)
    ax.set_xticks(xs); ax.set_xticklabels([f"{b} min" for b in bands], fontsize=7.4)
    ax.set_ylim(0, max(S["brampton"]["postings_within"]["90"] / 1e3 * 1.25, 1)); ax.set_xlim(25, 95)
    ax.grid(axis="y", color="#E8ECF0"); ax.set_axisbelow(True)
    legend(ax, [PN[p] for p in plants], [PC[p] for p in plants])
    prov = tp.groupby("provider").size().sort_values(ascending=False)
    ax = chart(fig, *R1[1], "Programs by provider", pl=0.09)
    hbar(ax, [clip(p_, 30) for p_ in prov.index], list(prov.values), colors=STEEL)
    lm = tp.assign(b=pd.cut(tp.months, [0, 1.5, 4, 9, 13, 99], labels=["≤1 mo", "2–4 mo", "5–9 mo", "10–13 mo", "14+ mo"])).groupby("b", observed=False).size()
    vbar(chart(fig, *R1[2], "Program length (programs)"), list(lm.index), list(lm.values), colors=[GREEN, GREEN, AMBER, AMBER, RED], wrap=8)
    for slot, p in zip(R2, plants):
        t = tp.sort_values(f"min_{p}").head(10)
        ax = chart(fig, *slot, f"Nearest programs to {PN[p]} (drive minutes; length in months)", pl=0.17)
        hbar(ax, [f"{clip(pg, 30)} · {clip(pv, 18)} ({m:.0f} mo)" for pg, pv, m in zip(t.program, t.provider, t.months)], list(t[f"min_{p}"]),
             fmt="{:.0f} min", colors=[GREEN if v <= 45 else AMBER if v <= 75 else RED for v in t[f"min_{p}"]])
    figs.append(fig)

    # 5 New products: workforce fit -----------------------------------------------------------------
    rb = rp[rp.plant == "brampton"].sort_values("share_quick", ascending=False)
    rb = rb.assign(retrain=rb.filled_retrain / rb.jobs, outside=rb.outside_hires / rb.jobs)
    fig = frame(5, [("factory", f"{len(rb)}", "Candidate products tested"), ("check", f"{rb.share_quick.iloc[0]:.0%}", clip(f"Ready in 6 months: {rb.product_name.iloc[0]}", 34)),
                    ("swap", f"{(rb.share_quick >= 0.75).sum()} of {len(rb)}", "Products 75%+ ready in 6 months"),
                    ("warn", f"{rb.share_quick.iloc[-1]:.0%}", "Aerospace ready in 6 months"),
                    ("edu", f"{rb.set_index('product').loc['defence', 'trained_workers'] if 'defence' in set(rb['product']) else 0:,.0f}", "Brampton retrained, armoured vehicles"),
                    ("people", f"{int(rb.jobs.iloc[0]):,}", "Hourly jobs per product (sized to plant)")],
                "Staffing from US BLS OEWS May 2025 for the closest industry, mapped to NOC 2021; each product sized to re-employ every laid-off worker. "
                "Ready = match 75+ and up to 6 months' training; retrained = match 65+ and up to 24 months.")
    stack_h(chart(fig, *R2[0], "Brampton: how each product's hourly jobs get filled", pl=0.13),
            [clip(n, 40) for n in rb.product_name], [("Ready within 6 months", list(rb.share_quick), STEEL), ("After retraining (≤2 yrs)", list(rb.retrain), AMBER),
                                                     ("Hire from outside", list(rb.outside), RED)])
    rk = rp[rp.plant == "cami"].set_index("product").loc[rb["product"]]
    grouped(chart(fig, *R2[1], "Average skill match of the workers placed, by product"), [clip(n, 22) for n in rb.product_name],
            [(PN["brampton"], list(rb.avg_match.round(0)), STEEL), (PN["cami"], list(rk.avg_match.round(0)), AMBER)], wrap=10, fs=6.6)
    for slot, prod in zip(R1, ["defence", "rail", "aero"]):
        f_ = fl[(fl.plant == "brampton") & (fl["product"] == prod) & (fl.stage != "quick")].groupby(["origin_name", "role_name"]).workers.sum().sort_values(ascending=False).head(5)
        name = rp.set_index(["plant", "product"]).loc[("brampton", prod), "product_name"] if ("brampton", prod) in rp.set_index(["plant", "product"]).index else prod
        ax = chart(fig, *slot, f"{clip(name, 34)}: retraining moves (Brampton)", pl=0.13)
        if len(f_):
            hbar(ax, [f"{SHORT.get(o, clip(o, 18))} → {clip(r_, 26)}" for o, r_ in f_.index], list(f_.values), colors=AMBER)
        else:
            ax.text(0.5, 0.5, "No retraining needed", ha="center", va="center", transform=ax.transAxes, color=MUTED)
    figs.append(fig)

    # 6 New products: trade-offs --------------------------------------------------------------------
    fig = frame(6, [("money", f"{rb.pay_vs_auto.max():.0%}", "Best pay vs auto (Brampton)"), ("money", f"{rk.pay_vs_auto.min():.0%}", "Lowest pay vs auto (Ingersoll)"),
                    ("people", f"{rb.salaried_per_100.min():.0f}", "Fewest salaried per 100 hourly"), ("people", f"{rb.salaried_per_100.max():.0f}", "Most salaried per 100 hourly"),
                    ("history", f"{rb.train_person_months.min() / 1e3:.1f}K", "Fewest training person-months"),
                    ("history", f"{rb.train_person_months.max() / 1e3:.1f}K", "Most training person-months")],
                "Pay compares ESDC regional median wages for the product's jobs with those for the plant's jobs. Workforce fit only: buyers, capital and the owners' plans also decide.")
    ax = chart(fig, *R2[0], "Fit vs pay: share ready in 6 months against pay vs auto (Brampton; bubble = salaried per 100)", pl=0.035, pb=0.03)
    ax.scatter(100 * rb.share_quick, 100 * rb.pay_vs_auto, s=rb.salaried_per_100 * 6, color=STEEL, alpha=0.55, edgecolors=SHEET, linewidths=0.8)
    for k, (_, r) in enumerate(rb.iterrows(), start=1):
        ax.text(100 * r.share_quick, 100 * r.pay_vs_auto, str(k), ha="center", va="center", fontsize=7, weight="bold", color=BAND)
    key = "\n".join(f"{k}  {clip(n.split(' (')[0], 30)}" for k, n in enumerate(rb.product_name, start=1))
    ax.text(0.30, 0.04, key, transform=ax.transAxes, fontsize=6.7, color=INK, va="bottom", linespacing=1.35,
            bbox=dict(boxstyle="round,pad=0.4", fc=CHIP, ec="none"))
    ax.set_xlabel("Ready within 6 months (%)", fontsize=7.6, color=MUTED); ax.set_ylabel("Pay vs auto jobs (%)", fontsize=7.6, color=MUTED)
    ax.set_yticks([70, 80, 90, 100, 110]); ax.tick_params(labelsize=7, colors=MUTED)
    ax.set_xlim(30, 105); ax.set_ylim(min(65, 100 * rb.pay_vs_auto.min() - 5), 100 * rb.pay_vs_auto.max() + 8)
    ax.grid(color="#E8ECF0", lw=0.7); ax.set_axisbelow(True)
    grouped(chart(fig, *R2[1], "Typical pay vs auto jobs, by product (%)"), [clip(n.split(" (")[0], 22) for n in rb.product_name],
            [(PN["brampton"], list((100 * rb.pay_vs_auto).round()), STEEL), (PN["cami"], list((100 * rk.pay_vs_auto).round()), AMBER)], wrap=10, fs=6.6)
    sp = rb.sort_values("salaried_per_100")
    ax = chart(fig, *R1[0], "Salaried hires per 100 hourly jobs", pl=0.10)
    hbar(ax, [clip(n.split(" (")[0], 28) for n in sp.product_name], list(sp.salaried_per_100), colors=[RED if v > 100 else STEEL for v in sp.salaried_per_100])
    tpm = rb.sort_values("train_person_months")
    ax = chart(fig, *R1[1], "Retraining effort: person-months of training (Brampton)", pl=0.10)
    hbar(ax, [clip(n.split(" (")[0], 28) for n in tpm.product_name], list(tpm.train_person_months), colors=AMBER)
    oh = rb.sort_values("outside_hires")
    ax = chart(fig, *R1[2], "Hourly jobs needing outside hires (Brampton)", pl=0.10)
    hbar(ax, [clip(n.split(" (")[0], 28) for n in oh.product_name], list(oh.outside_hires), colors=[RED if v > 200 else SKY for v in oh.outside_hires])
    figs.append(fig)

    out_dir.mkdir(parents=True, exist_ok=True)
    with PdfPages(out_dir / "next_shift_dashboards.pdf") as pdf:
        for f, name in zip(figs, FILES):
            f.savefig(out_dir / f"{name}.png", dpi=220, facecolor=BG)
            pdf.savefig(f, facecolor=BG)
            plt.close(f)
    return [out_dir / f"{n}.png" for n in FILES]


if __name__ == "__main__":
    print(build())
