import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.express as px

# Sample Data for Plot
df = px.data.iris()
fig = px.scatter(df, x='sepal_width', y='sepal_length')

# Initialize the Dash app with a Bootstrap theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Layout of the app
app.layout = dbc.Container([
    # Top bar with title
    dbc.NavbarSimple(
        children=[
            html.H1("Dashboard Title", className="navbar-brand mb-0", style={"font-size": "2rem"}),
        ],
        brand="",
        color="#f8f9fa",
        dark=False,
        style={"height": "4rem", "background-color": "#f8f9fa"}
    ),
    
    # Content area with Sidebar and Plot
    dbc.Row([
        # Sidebar
        dbc.Col(
            dbc.Nav([
                dbc.NavLink("Home", href="#", active="exact"),
                dbc.NavLink("Link 1", href="#", active="exact"),
                dbc.NavLink("Link 2", href="#", active="exact"),
            ], vertical=True, pills=True),
            width=3, style={"background-color": "#e9ecef", "height": "100vh"}
        ),
        
        # Plot area
        dbc.Col(
            dcc.Graph(figure=fig),
            width=9
        )
    ])
], fluid=True)

if __name__ == '__main__':
    app.run_server(debug=True)