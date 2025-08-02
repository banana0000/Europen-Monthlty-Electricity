import plotly.express as px
import pandas as pd
from dash import Dash, dcc, html, Input, Output, State, ctx
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

# --- 1. Data Loading and Preparation ---

df = pd.read_csv('monthly.csv')
df['Date'] = pd.to_datetime(df['Date'])
df['Year'] = df['Date'].dt.year
df['Month'] = df['Date'].dt.month
if 'Day' not in df.columns:
    df['Day'] = 1  # fallback if no daily data

ALL_COUNTRIES = sorted(df['Area'].unique())

# Only CO2 metric
METRIC_LABEL = 'CO₂ Intensity (gCO2e/kWh)'
METRIC_DETAILS = {
    'Category': 'Power sector emissions',
    'Variable': 'CO2 intensity'
}

# --- 2. Initialize Dash App ---
app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
server = app.server

# --- 3. App Layout ---
app.layout = dbc.Container([
    dbc.Row(
        dbc.Col(
            html.H1(
                "European CO2 Intensity 2015 - 2025",
                className="text-primary my-4",
                style={'textAlign': 'left'}
            ),
            width=12
        )
    ),

    dbc.Row([
        dbc.Col([
            html.Label("Select Countries:", className="fw-bold text-center"),
            dcc.Dropdown(
                id='country-multiselect-dropdown',
                options=[{'label': country, 'value': country} for country in ALL_COUNTRIES],
                value=['Germany', 'Cyprus', 'Portugal'],
                multi=True,
                clearable=False
            )
        ], width=6),
    ], className="mb-4 justify-content-center align-items-center"),

    dbc.Row([
        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    dcc.Graph(id='multi-country-line-chart', figure={}, style={'height': '500px'})
                ]),
                className="shadow-sm h-100"
            ),
            lg=7, md=12, className="mb-4 mb-lg-0"
        ),

        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    dcc.Graph(id='heatmap-chart', figure={}, style={'height': '500px'}),
                ]),
                className="shadow-sm h-100"
            ),
            lg=5, md=12
        ),
    ]),
    html.Br(),

    dbc.Row([
        dbc.Col([
            html.Button("Start animation", id="start-stop-btn", n_clicks=0, className="btn btn-primary"),
            dcc.Store(id="animation-running", data=False)
        ], width="auto"),
    ], className="mb-4"),

    dcc.Interval(
        id='interval-component',
        interval=2000,  # 2000 ms = 2 seconds
        n_intervals=0,
        disabled=True  # start as disabled
    )

], fluid=True, className="bg-light p-4")


# --- 4. Button Callback: Start/Stop animation ---
@app.callback(
    Output("animation-running", "data"),
    Output("start-stop-btn", "children"),
    Output("interval-component", "disabled"),
    Input("start-stop-btn", "n_clicks"),
    State("animation-running", "data"),
    prevent_initial_call=True
)
def toggle_animation(n_clicks, running):
    # Toggle the running state
    if running:
        return False, "Start animation", True
    else:
        return True, "Stop animation", False

# --- 5. Interval Callback to Animate Countries (stacked) ---
@app.callback(
    Output('country-multiselect-dropdown', 'value'),
    [Input('interval-component', 'n_intervals')],
    [State('country-multiselect-dropdown', 'value')]
)
def animate_countries(n_intervals, current_selection):
    n = (n_intervals % len(ALL_COUNTRIES)) + 1
    return ALL_COUNTRIES[:n]

# --- 6. Callback to Update Charts ---
@app.callback(
    Output('multi-country-line-chart', 'figure'),
    Output('heatmap-chart', 'figure'),
    [Input('country-multiselect-dropdown', 'value')]
)
def update_charts(selected_countries):
    category = METRIC_DETAILS['Category']
    variable = METRIC_DETAILS['Variable']

    dff_line = df[
        (df['Area'].isin(selected_countries)) &
        (df['Category'] == category) &
        (df['Variable'] == variable)
    ]

    # --- Spline Line Chart with min/max markers ---
    if dff_line.empty:
        line_fig = go.Figure().update_layout(
            title_text="Please select at least one country",
            template='plotly_white'
        )
    else:
        line_fig = go.Figure()
        for area in dff_line['Area'].unique():
            area_df = dff_line[dff_line['Area'] == area].sort_values('Date')
            line_fig.add_trace(go.Scatter(
                x=area_df['Date'],
                y=area_df['Value'],
                mode='lines',
                name=area,
                line_shape='spline'
            ))
            # Min and max markers
            min_idx = area_df['Value'].idxmin()
            max_idx = area_df['Value'].idxmax()
            for idx, marker_color in [
                (min_idx, 'red'),
                (max_idx, 'green')
            ]:
                if pd.notna(idx):
                    line_fig.add_trace(go.Scatter(
                        x=[area_df.loc[idx, 'Date']],
                        y=[area_df.loc[idx, 'Value']],
                        mode='markers',
                        marker=dict(color=marker_color, size=12, symbol='circle'),
                        name=f"{area} {'min' if marker_color=='red' else 'max'}",
                        showlegend=False
                    ))
        line_fig.update_layout(
            transition_duration=500,
            legend_title_text='Country',
            title={
                'text': f"{METRIC_LABEL} by Country Over Time",
                'x': 0.5,
                'xanchor': 'center'
            },
            template='plotly_white'
        )

    # --- Heatmap: év (x) vs ország (y), átlag ---
    dff_heatmap = df[
        (df['Area'].isin(selected_countries)) &
        (df['Category'] == category) &
        (df['Variable'] == variable)
    ]
    pivot = dff_heatmap.groupby(['Area', 'Month'])['Value'].mean().unstack(fill_value=0)

    if pivot.empty:
        heatmap_fig = go.Figure()
        heatmap_fig.update_layout(
            title="No data for selected countries.",
            template='plotly_white'
        )
    else:
        heatmap_fig = px.imshow(
            pivot,
            aspect="auto",
            color_continuous_scale='YlGnBu',
            labels=dict(x="Month", y="Country", color="Average Value"),
            template='plotly_white'
        )
        heatmap_fig.update_layout(
            transition_duration=300,
            title="Country CO2 Monthly "
        )

    return line_fig, heatmap_fig

# --- 7. Run the App ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)