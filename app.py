import json
import base64
import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import pandas as pd

# 1. LOAD THE DATA

df_inc = pd.read_csv("incidence.csv")
df_mort = pd.read_csv("mortality.csv")
df_age_inc = pd.read_csv("incidence_by_age.csv")
df_age_mort = pd.read_csv("mortality_by_age.csv")
df_reg_inc = pd.read_csv("incidence_by_region.csv")
df_reg_mort = pd.read_csv("mortality_by_region.csv")

with open("clinical_data.json", "r", encoding="utf-8") as f:
    clinical_data = json.load(f)

cases_2023 = df_inc[df_inc["Rok"] == 2023]["Liczba zachorowań"].values[0]
deaths_2023 = df_mort[df_mort["Rok"] == 2023]["Liczba zgonów"].values[0]
age_cols = [c for c in df_age_inc.columns if c != "Rok"]
peak_age_inc = df_age_inc[df_age_inc["Rok"] == 2023][age_cols].idxmax(axis=1).values[0]
peak_age_mort = df_age_mort[df_age_mort["Rok"] == 2023][age_cols].idxmax(axis=1).values[0]

raw_diag = clinical_data.get("diagnosis", [])
df_diag = pd.DataFrame(raw_diag).rename(columns={
    "test": "Test", "phase": "Phase", "clinical_use": "Clinical Use",
    "sensitivity": "Sensitivity (%)", "specificity": "Specificity (%)",
})
df_diag["Sensitivity (%)"] = df_diag["Sensitivity (%)"].str.replace("%", "").astype(float)
df_diag["Specificity (%)"] = df_diag["Specificity (%)"].str.replace("%", "").astype(float)

raw_treat = clinical_data.get("treatment", [])
treat_descriptions = {item["figo_stage"]: item.get("description", "") for item in raw_treat}
df_treat = pd.DataFrame(raw_treat).rename(columns={
    "figo_stage": "FIGO Stage", "primary_treatment": "Primary Treatment",
    "fertility_sparing": "Fertility Sparing", "five_year_survival": "5-Year Survival (%)",
    "description": "Description",
})
df_treat["5-Year Survival (%)"] = df_treat["5-Year Survival (%)"].str.replace("%", "").astype(float)

about = clinical_data.get("about", {})
key_facts = about.get("key_facts_poland", [])
how_to = about.get("how_to_use", [])
disclaimer = about.get("disclaimer", "")

# 2. STYLING CONSTANTS

BRAND   = "#AD1457"   
ACCENT  = "#6A1B9A"   
BRAND2  = "#F06292"  
TEXT    = "#2c3e50"
MUTED   = "#9e9e9e"
BG      = "#FFF5F8"   
CARD_BG = "#ffffff"

tab_style = {
    "borderBottom": "2px solid #f0d0dc",
    "padding": "8px 18px",
    "fontWeight": "600",
    "color": MUTED,
    "backgroundColor": "white",
    "fontSize": "0.92rem",
}
tab_selected_style = {
    "borderTop": f"3px solid {BRAND}",
    "borderBottom": "2px solid white",
    "padding": "8px 18px",
    "fontWeight": "700",
    "color": BRAND,
    "backgroundColor": "white",
    "fontSize": "0.92rem",
}
card_style = {
    "boxShadow": "0 4px 16px rgba(173,20,87,0.10)",
    "padding": "24px 20px",
    "borderRadius": "14px",
    "textAlign": "center",
    "backgroundColor": CARD_BG,
    "flex": "1",
    "margin": "8px",
    "borderTop": f"4px solid {BRAND}",
}

# 3. FIGURE BUILDER FUNCTIONS

def build_trend_fig(years):
    fi = df_inc[(df_inc["Rok"] >= years[0]) & (df_inc["Rok"] <= years[1])]
    fm = df_mort[(df_mort["Rok"] >= years[0]) & (df_mort["Rok"] <= years[1])]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=fi["Rok"], y=fi["Liczba zachorowań"],
                             mode="lines+markers", name="Incidence",
                             line=dict(color=BRAND, width=3),
                             marker=dict(size=7)))
    fig.add_trace(go.Scatter(x=fm["Rok"], y=fm["Liczba zgonów"],
                             mode="lines+markers", name="Mortality",
                             line=dict(color=ACCENT, width=3),
                             marker=dict(size=7)))
    fig.update_layout(
        xaxis_title="Year", yaxis_title="Number of Cases",
        template="simple_white", legend=dict(orientation="h", y=1.1),
        margin={"t": 20}, transition_duration=500
    )
    return fig

def build_age_fig(selected_year, measure="BOTH"):
    row_inc = df_age_inc[df_age_inc["Rok"] == selected_year].drop(columns=["Rok"])
    row_mort = df_age_mort[df_age_mort["Rok"] == selected_year].drop(columns=["Rok"])
    categories = row_inc.columns.tolist()
    fig = go.Figure()
    if measure in ["INC", "BOTH"]:
        fig.add_trace(go.Bar(x=categories, y=row_inc.values[0],
                             name="Incidence", marker_color=BRAND))
    if measure in ["MORT", "BOTH"]:
        fig.add_trace(go.Bar(x=categories, y=row_mort.values[0],
                             name="Mortality", marker_color=ACCENT))
    fig.update_layout(
        barmode="group",
        xaxis=dict(title="Age Group", type="category"),
        yaxis_title="Cases",
        template="simple_white",
        clickmode="event+select",
        margin={"t": 10}, transition_duration=500
    )
    return fig

def build_region_fig(selected_regions, measure):
    if not selected_regions:
        return go.Figure()
    f_inc = df_reg_inc[df_reg_inc["Region"].isin(selected_regions)]
    f_mort = df_reg_mort[df_reg_mort["Region"].isin(selected_regions)]
    fig = go.Figure()
    if measure in ["INC", "BOTH"]:
        fig.add_trace(go.Bar(x=f_inc["Region"], y=f_inc["Liczba zachorowań"],
                             name="Incidence", marker_color=BRAND))
    if measure in ["MORT", "BOTH"]:
        fig.add_trace(go.Bar(x=f_mort["Region"], y=f_mort["Liczba zgonów"],
                             name="Mortality", marker_color=ACCENT))
    fig.update_layout(
        barmode="group",
        xaxis_title="Voivodeship", yaxis_title="Cumulative Cases",
        template="simple_white", margin={"t": 10}, transition_duration=500
    )
    return fig

def build_diag_fig(selected_rows):
    if not selected_rows:
        return go.Figure()
    dff = df_diag.iloc[selected_rows]
    color_map = {"Screening": BRAND, "Diagnosis": ACCENT, "Staging": BRAND2}
    fig = go.Figure()
    for _, row in dff.iterrows():
        fig.add_trace(go.Scatter(
            x=[row["Sensitivity (%)"]],
            y=[row["Specificity (%)"]],
            mode="markers+text",
            text=[row["Test"]],
            textposition="top center",
            marker=dict(size=22, color=color_map.get(row["Phase"], "#95a5a6"), opacity=0.85),
            name=row["Phase"],
            hovertemplate=(
                f"<b>{row['Test']}</b><br>"
                f"Phase: {row['Phase']}<br>"
                f"Use: {row['Clinical Use']}<br>"
                f"Sensitivity: {row['Sensitivity (%)']}%<br>"
                f"Specificity: {row['Specificity (%)']}%<extra></extra>"
            ),
            showlegend=False,
        ))
    fig.update_xaxes(range=[50, 100], title_text="Sensitivity (%)")
    fig.update_yaxes(range=[75, 100], title_text="Specificity (%)")
    fig.update_layout(template="simple_white", margin={"t": 20}, transition_duration=500)
    return fig

def build_treatment_fig(selected_stage=None, stage_filter="ALL"):
    dff = df_treat.copy()
    if stage_filter == "EARLY":
        dff = dff[dff["FIGO Stage"].str.startswith(("I", "II")) & ~dff["FIGO Stage"].str.startswith("III")]
    elif stage_filter == "LATE":
        dff = dff[dff["FIGO Stage"].str.startswith(("III", "IV"))]

    colors = [ACCENT if row["FIGO Stage"] == selected_stage else BRAND2
              for _, row in dff.iterrows()]
    fig = go.Figure(go.Bar(
        x=dff["FIGO Stage"],
        y=dff["5-Year Survival (%)"],
        marker_color=colors,
        text=dff["5-Year Survival (%)"].apply(lambda x: f"{x:.0f}%"),
        textposition="auto",
        hovertemplate="<b>%{x}</b><br>5-Year Survival: %{y}%<extra></extra>",
    ))
    fig.update_layout(
        xaxis_title="FIGO Stage",
        yaxis=dict(title="Survival (%)", range=[0, 110]),
        template="simple_white",
        clickmode="event",
        margin={"t": 40}, transition_duration=500
    )
    return fig

def _treat_info(row):
    return html.Div([
        html.H4("Description", style={"color": BRAND, "marginTop": 0, "marginBottom": "12px",
                                      "textTransform": "uppercase", "letterSpacing": "1px",
                                      "fontSize": "0.95rem"}),
        html.H5(f"Stage {row['FIGO Stage']}", style={"color": ACCENT, "marginTop": 0, "marginBottom": "8px"}),
        html.P([html.Strong("📋 Description: "), row["Description"]]),
        html.P([html.Strong("💉 Primary treatment: "), row["Primary Treatment"]]),
        html.P([html.Strong("🌸 Fertility sparing: "), row["Fertility Sparing"]]),
        html.P([html.Strong("📈 5-year survival: "), f"{row['5-Year Survival (%)']:.0f}%"]),
    ])

def build_rf_chart(rf_list, selected_factor=None):
    labels = [item["factor"] for item in rf_list]
    magnitudes = [10, 7, 6, 5, 5, 4, 4, 3, 3, 3][:len(labels)]

    colors = [ACCENT if label == selected_factor else BRAND for label in labels]
    
    fig = go.Figure(go.Bar(
        x=magnitudes, y=labels, orientation="h",
        marker_color=colors, text=magnitudes, textposition="auto",
    ))
    fig.update_layout(
        xaxis_title="Relative Risk Weight (illustrative)",
        yaxis={"categoryorder": "total ascending"},
        template="simple_white", margin={"t": 10}, height=340,
        transition_duration=500
    )
    return fig

# 4. APP + LAYOUT

app = dash.Dash(__name__, title="CervixPL Dashboard", suppress_callback_exceptions=True)
server = app.server

_DEFAULT_YEAR = int(df_inc["Rok"].max())
_DEFAULT_REGIONS = ["Mazowieckie", "Wielkopolskie", "Śląskie"]

app.layout = html.Div(
    style={"fontFamily": "Segoe UI, Arial, sans-serif", "backgroundColor": BG, "minHeight": "100vh"},
    children=[
        # Header
        html.Div(
            style={
                "display": "flex", "alignItems": "center",
                "padding": "20px 40px",
                "background": f"linear-gradient(135deg, {BRAND} 0%, {ACCENT} 100%)",
                "boxShadow": "0 4px 12px rgba(173,20,87,0.25)",
            },
            children=[
                html.Span("🎗️", style={
                    "fontSize": "52px",
                    "marginRight": "18px",
                    "flexShrink": "0",
                    "filter": "hue-rotate(160deg) saturate(2)",
                    "lineHeight": "1",
                }),
                html.Div([
                    html.H1("CervixPL", style={
                        "margin": 0, "color": "white",
                        "fontSize": "2rem", "letterSpacing": "2px",
                        "textShadow": "0 1px 4px rgba(0,0,0,0.2)",
                    }),
                    html.P("Cervical Neoplasms: Invasive & In Situ (C53 + D06) - Poland",
                           style={"margin": 0, "color": "rgba(255,255,255,0.82)", "fontSize": "0.85rem"}),
                ]),
            ],
        ),

        # Tabs
        html.Div(
            style={"padding": "0 40px", "backgroundColor": "white"},
            children=[
                dcc.Tabs(
                    id="tabs-dashboard",
                    value="tab-1",
                    style={"borderBottom": "2px solid #e0e0e0"},
                    children=[
                        dcc.Tab(label="🏠 Overview",      value="tab-1", style=tab_style, selected_style=tab_selected_style),
                        dcc.Tab(label="📊 Epidemiology",  value="tab-2", style=tab_style, selected_style=tab_selected_style),
                        dcc.Tab(label="⚠️ Risk Factors",  value="tab-3", style=tab_style, selected_style=tab_selected_style),
                        dcc.Tab(label="🔬 Diagnosis",     value="tab-4", style=tab_style, selected_style=tab_selected_style),
                        dcc.Tab(label="💊 Treatment",     value="tab-5", style=tab_style, selected_style=tab_selected_style),
                        dcc.Tab(label="ℹ️ About & Help",  value="tab-6", style=tab_style, selected_style=tab_selected_style),
                    ],
                ),
            ],
        ),
        html.Div(id="tabs-content", style={"padding": "30px 40px"}),
    ],
)

# 5. TAB CONTENT CALLBACK

@app.callback(Output("tabs-content", "children"), Input("tabs-dashboard", "value"))
def render_content(tab):

    if tab == "tab-1":
        year_min = int(df_inc["Rok"].min())
        year_max = int(df_inc["Rok"].max())
        return html.Div([
            html.Div(
                style={"display": "flex", "justifyContent": "space-between", "marginBottom": "20px"},
                children=[
                    html.Div(style=card_style, children=[
                        html.Div("🆕", style={"fontSize": "2rem", "marginBottom": "6px"}),
                        html.P("New Cases (2023)", style={"color": MUTED, "marginBottom": "6px", "fontWeight": "600"}),
                        html.H2(f"{int(cases_2023):,}".replace(",", " "),
                                style={"color": BRAND, "margin": 0}),
                    ]),
                    html.Div(style=card_style, children=[
                        html.Div("💔", style={"fontSize": "2rem", "marginBottom": "6px"}),
                        html.P("Deaths (2023)", style={"color": MUTED, "marginBottom": "6px", "fontWeight": "600"}),
                        html.H2(f"{int(deaths_2023):,}".replace(",", " "),
                                style={"color": ACCENT, "margin": 0}),
                    ]),
                    html.Div(style=card_style, children=[
                        html.Div("👩", style={"fontSize": "2rem", "marginBottom": "6px"}),
                        html.P("Peak Risk Age", style={"color": MUTED, "marginBottom": "6px", "fontWeight": "600"}),
                        html.H2(f"{peak_age_inc}",
                                style={"color": BRAND2, "margin": 0, "fontSize": "1.3rem"}),
                    ]),
                    html.Div(style=card_style, children=[
                        html.Div("📆", style={"fontSize": "2rem", "marginBottom": "6px"}),
                        html.P("Data Period", style={"color": MUTED, "marginBottom": "6px", "fontWeight": "600"}),
                        html.H2(f"{year_min}-{year_max}", style={"color": TEXT, "margin": 0}),
                    ]),
                ],
            ),
            html.Div([
                html.H3("Incidence and Mortality Over Time",
                        style={"color": TEXT, "marginBottom": "8px"}),
                html.Label("Select year range:", style={"fontWeight": "600", "color": TEXT}),
                dcc.RangeSlider(
                    id="year-slider",
                    min=year_min, max=year_max,
                    value=[year_min, year_max],
                    marks={str(y): str(y) for y in range(year_min, year_max + 1, 2)},
                    step=1,
                ),
                dcc.Graph(id="trend-line-chart",
                          figure=build_trend_fig([year_min, year_max])),
            ]),
        ])

    elif tab == "tab-2":
        all_regions = sorted(df_reg_inc["Region"].unique())
        default_year = int(df_age_inc["Rok"].max())
        return html.Div([
            html.Div(
                style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "24px"},
                children=[
                    html.Div([
                        html.H4("Incidence & Mortality by Age Group", style={"color": TEXT}),
                        html.Label("Select year:"),
                        dcc.Dropdown(
                            id="epid-age-year-dropdown",
                            options=[{"label": str(y), "value": y}
                                     for y in sorted(df_age_inc["Rok"].unique())],
                            value=default_year,
                            clearable=False,
                        ),
                        html.Label("Measure:", style={"marginTop": "10px", "display": "block"}),
                        dcc.RadioItems(
                            id="age-measure-radio",
                            options=[
                                {"label": "  Incidence", "value": "INC"},
                                {"label": "  Mortality", "value": "MORT"},
                                {"label": "  Both",      "value": "BOTH"},
                            ],
                            value="BOTH",
                            inline=True,
                            style={"marginBottom": "8px"},
                        ),
                        dcc.Graph(id="age-bar-chart",
                                  figure=build_age_fig(default_year, "BOTH")),
                        html.Div(
                            id="age-trend-container",
                            children=html.P(
                                "💡 Click a bar above to see the trend for that age group over all years.",
                                style={"color": MUTED, "fontStyle": "italic", "marginTop": "8px"},
                            ),
                        ),
                    ]),
                    html.Div([
                        html.H4("Incidence & Mortality by Region (cumulative)", style={"color": TEXT}),
                        html.Label("Select regions:"),
                        dcc.Dropdown(
                            id="epid-region-dropdown",
                            options=[{"label": r, "value": r} for r in all_regions],
                            value=_DEFAULT_REGIONS,
                            multi=True,
                        ),
                        html.Label("Measure:", style={"marginTop": "10px", "display": "block"}),
                        dcc.RadioItems(
                            id="epid-measure-radio",
                            options=[
                                {"label": "  Incidence", "value": "INC"},
                                {"label": "  Mortality", "value": "MORT"},
                                {"label": "  Both",      "value": "BOTH"},
                            ],
                            value="BOTH",
                            inline=True,
                            style={"marginBottom": "8px"},
                        ),
                        dcc.Graph(id="region-bar-chart",
                                  figure=build_region_fig(_DEFAULT_REGIONS, "BOTH")),
                    ]),
                ],
            ),
        ])

    elif tab == "tab-3":
        rf_list = clinical_data.get("risk_factors", [])
        default_factor = rf_list[0]["factor"] if rf_list else None
        first_match = rf_list[0] if rf_list else None
        initial_info = html.Div([
            html.H4(first_match["factor"], style={"color": BRAND, "marginTop": 0}),
            html.P([html.Strong("Mechanism: "), first_match["description"]]),
            html.P([html.Strong("Prevention: "), first_match["prevention"]]),
        ]) if first_match else html.P("No data.")
        return html.Div([
            html.H4("⚠️ Main Risk Factors and Prevention", style={"color": BRAND}),
            html.P("Select a risk factor to view its mechanism and highlight it on the chart."),
            dcc.Dropdown(
                id="rf-dropdown",
                options=[{"label": item["factor"], "value": item["factor"]} for item in rf_list],
                value=default_factor,
                clearable=False,
            ),
            html.Div(
                id="rf-info-box",
                style={
                    "marginTop": "20px", "padding": "24px",
                    "border": f"1px solid {BRAND2}", "borderRadius": "12px",
                    "backgroundColor": "#FFF0F5",
                    "boxShadow": "0 2px 10px rgba(173,20,87,0.08)",
                },
                children=initial_info,
            ),
            html.Hr(),
            html.H4("📊 Risk Factor Overview - Relative Severity",
                    style={"color": BRAND, "marginTop": "20px"}),
            dcc.Graph(id="rf-chart", figure=build_rf_chart(rf_list, default_factor)),
        ])

    elif tab == "tab-4":
        all_rows = list(range(len(df_diag)))
        return html.Div([
            html.H4("🔬 Diagnostic Procedures", style={"color": BRAND}),
            html.P("Select rows in the table to highlight the tests on the scatter chart."),
            dash_table.DataTable(
                id="diag-table",
                columns=[{"name": c, "id": c} for c in df_diag.columns],
                data=df_diag.to_dict("records"),
                row_selectable="multi",
                selected_rows=all_rows,
                style_table={"overflowX": "auto", "marginBottom": "20px"},
                style_cell={"textAlign": "left", "padding": "10px",
                            "fontFamily": "Segoe UI, sans-serif"},
                style_header={"backgroundColor": "#f4f4f4", "fontWeight": "bold"},
                style_data_conditional=[
                    {"if": {"state": "selected"},
                     "backgroundColor": "#fdecea", "border": f"1px solid {BRAND}"},
                ],
            ),
            html.H3("Sensitivity vs. Specificity of Diagnostic Tests",
                    style={"color": TEXT, "marginBottom": "8px", "marginTop": "16px"}),
            dcc.Graph(id="diag-bubble-plot",
                      figure=build_diag_fig(all_rows)),
        ])

    elif tab == "tab-5":
        return html.Div([
            html.H4("💊 Treatment Protocols by FIGO Stage", style={"color": BRAND}),
            html.P("Filter stages using the buttons below, and click a bar to see the stage description."),
            
            dcc.RadioItems(
                id="treat-stage-filter",
                options=[
                    {"label": " All Stages", "value": "ALL"},
                    {"label": " Early Stages (I-II)", "value": "EARLY"},
                    {"label": " Late Stages (III-IV)", "value": "LATE"},
                ],
                value="ALL",
                inline=True,
                style={"marginBottom": "15px", "fontWeight": "600"}
            ),

            html.H3("5-Year Survival Rate by FIGO Stage",
                    style={"color": TEXT, "marginBottom": "8px", "marginTop": "8px"}),
            dcc.Graph(id="treat-survival-chart",
                      figure=build_treatment_fig(None, "ALL")),
            html.Div(
                id="treat-info-box",
                style={
                    "margin": "16px 0",
                    "padding": "18px 24px",
                    "border": f"1px solid {BRAND2}",
                    "borderRadius": "12px",
                    "backgroundColor": "#FFF0F5",
                    "boxShadow": "0 2px 10px rgba(173,20,87,0.08)",
                },
                children=html.P("Click a bar to see the stage description.",
                                style={"color": MUTED, "fontStyle": "italic"}),
            ),
        ])

    elif tab == "tab-6":
        return html.Div([
            html.Div(
                style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "32px"},
                children=[
                    html.Div([
                        html.H4("🎗️ About this Dashboard", style={"color": BRAND}),
                        html.P(about.get("description", "")),
                        html.P(
                            [html.Strong("Technologies: ")]
                            + [html.Span(t + "  ") for t in about.get("tags", [])],
                            style={"color": MUTED},
                        ),
                    ]),
                    html.Div([
                        html.H4("🖱️ How to Use", style={"color": BRAND}),
                        html.Ul([html.Li(step) for step in how_to]),
                    ]),
                ],
            ),
            html.Hr(),
            html.H4("📌 Key Facts - Cervical Cancer in Poland", style={"color": BRAND}),
            html.Ul([html.Li(fact) for fact in key_facts]),
            html.Hr(),
            html.Footer(html.Small(f"Disclaimer: {disclaimer}", style={"color": MUTED})),
        ])

# 6. INTERACTIVE CALLBACKS

@app.callback(Output("trend-line-chart", "figure"), Input("year-slider", "value"))
def update_trend_chart(years):
    return build_trend_fig(years)

@app.callback(
    Output("age-bar-chart", "figure"),
    [Input("epid-age-year-dropdown", "value"), Input("age-measure-radio", "value")],
)
def update_age_chart(selected_year, measure):
    return build_age_fig(selected_year, measure)

@app.callback(Output("age-trend-container", "children"), Input("age-bar-chart", "clickData"))
def show_age_trend(click_data):
    if click_data is None:
        return html.P(
            "💡 Click a bar above to see the trend for that age group over all years.",
            style={"color": MUTED, "fontStyle": "italic", "marginTop": "8px"},
        )
    age_group = click_data["points"][0]["x"]
    if age_group not in df_age_inc.columns:
        return html.P(f"No data for group {age_group}.")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_age_inc["Rok"], y=df_age_inc[age_group],
                             mode="lines+markers", name="Incidence",
                             line=dict(color=BRAND, width=2), marker=dict(size=6)))
    fig.add_trace(go.Scatter(x=df_age_mort["Rok"], y=df_age_mort[age_group],
                             mode="lines+markers", name="Mortality",
                             line=dict(color=ACCENT, width=2), marker=dict(size=6)))
    fig.update_layout(
        title=dict(text=f"Trend for Age Group: {age_group}", y=0.97, x=0),
        xaxis_title="Year", yaxis_title="Cases",
        template="simple_white", margin={"t": 80, "b": 50},
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        transition_duration=500
    )
    return dcc.Graph(figure=fig)

@app.callback(
    Output("region-bar-chart", "figure"),
    [Input("epid-region-dropdown", "value"), Input("epid-measure-radio", "value")],
)
def update_region_chart(selected_regions, measure):
    return build_region_fig(selected_regions, measure)

@app.callback(
    [Output("rf-info-box", "children"), Output("rf-chart", "figure")], 
    Input("rf-dropdown", "value")
)
def update_rf_box(selected_factor):
    rf_list = clinical_data.get("risk_factors", [])
    match = next((item for item in rf_list if item["factor"] == selected_factor), None)
    
    updated_fig = build_rf_chart(rf_list, selected_factor)
    
    if match:
        info_div = html.Div([
            html.H4(match["factor"], style={"color": BRAND, "marginTop": 0}),
            html.P([html.Strong("Mechanism: "), match["description"]]),
            html.P([html.Strong("Prevention: "), match["prevention"]]),
        ])
        return info_div, updated_fig
    
    return html.P("Select a factor from the dropdown."), updated_fig

@app.callback(Output("diag-bubble-plot", "figure"), Input("diag-table", "selected_rows"))
def update_diag_plot(selected_rows):
    return build_diag_fig(selected_rows)

@app.callback(
    Output("treat-survival-chart", "figure"), 
    [Input("treat-survival-chart", "clickData"), Input("treat-stage-filter", "value")]
)
def update_treatment_chart(click_data, stage_filter):
    stage = click_data["points"][0]["x"] if click_data else None
    return build_treatment_fig(stage, stage_filter)

@app.callback(Output("treat-info-box", "children"), Input("treat-survival-chart", "clickData"))
def update_treat_info(click_data):
    if click_data is None:
        return html.P("Click a bar to see the stage description.",
                      style={"color": MUTED, "fontStyle": "italic"})
    stage = click_data["points"][0]["x"]
    row = df_treat[df_treat["FIGO Stage"] == stage].iloc[0]
    return _treat_info(row)

# 7. RUN

if __name__ == "__main__":
    app.run(debug=True)
