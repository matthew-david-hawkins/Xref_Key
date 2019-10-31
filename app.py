import base64
import datetime
import io
import math

import dash
from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_table
import pandas as pd
import plotly.graph_objs as go
import flask
import numpy as np

# ---------------------------------------
# -----------/ Functions /--------------
# ---------------------------------------

# ------------/  /--------------
# A function with accepts a path to a cross reference in csv format and returns two dataframes, one for analogs, and one for digitals
def split_xref(df):

    # Locate the start of the Digital I/O
    first_d = df.loc[df["#TYPE"] == "#TYPE"].index[0]

    # Create separate dataframes for the analogs and digitals
    a_df = df.iloc[0:first_d]

    # Save dataframe
    #a_df.to_csv("xref/analogs.csv")

    d_df = df.iloc[first_d:]

    # grab the first row for the header
    new_header = d_df.iloc[0] 

    # take the data less the header row
    d_df = d_df[1:] 

    # Reset the header
    d_df.columns = new_header

    # Save dataframe
    #d_df.to_csv("xref/digitals.csv")
    
    return (a_df, d_df)

# ------------/  /--------------
# A function with accepts a cross reference df and returns a list of the unique engine names
def get_engines(df):
    
    # Convert the FROM ENGINE and TO ENGINE columns to a list of unique engine
    to_engine = df["TO ENGINE"].to_list()
    
    from_engine = df["FROM ENGINE"].to_list()
           
    engines = list(set(to_engine + from_engine))
    
    # clean out Nan
    engines = [x for x in engines if (str(x) != 'nan' and str(x) != 'FROM ENGINE' and str(x) != 'TO ENGINE' and str(x) != '' and str(x) != 'None')]

    return (engines)

# ------------/  /--------------
# A function that grabs the SCP signal field and puts it in the MISC 5 column, and returns the number of number keys generated
def get_scp_field(df, scp_names):
    
    df = df.replace(np.nan, '', regex=True)
    to_engine = df.columns.get_loc("TO ENGINE")
    from_engine = df.columns.get_loc("FROM ENGINE")
    to_symbol = df.columns.get_loc("TO SYMBOL")
    from_symbol = df.columns.get_loc("FROM SYMBOL")
    equation = df.columns.get_loc("EQUATION")
    
    scp_lines = []
    
    key_count = 0 
    # Iterate over the rows
    for i in range(len(df)):
        
        scp_flag = False
        
        # Detect if the line is for an SCP engine
        for engine in scp_names:
            
            # If the to engine is an SCP, get the concatenation of the to symbol
            if (df.iloc[i, to_engine] == engine):
                
                scp_flag = True
                scp_lines.append(strip_scp(str(df.iloc[i, to_symbol])))
                key_count += 1
            
            # If the from engine is an SCP, get the concatenation of the from symbol and equation field
            elif (df.iloc[i, from_engine] == engine):

                scp_flag = True
                scp_lines.append(strip_scp(str(df.iloc[i, from_symbol]) + str(df.iloc[i, equation])))
                key_count += 1
            
        if scp_flag==False:
                
            scp_lines.append("")
        
    df["MISC5"] = scp_lines
    
            
    return df, key_count

# ------------/  /--------------
# A function which takes in an SCP string a returns only the compound:block.point
def strip_scp(my_string):
    
    # Find everything left off the semicolon
    scolon = my_string.find(":")

    scolon_left = my_string[0:scolon]

    # Reverse the string to perform find in backward direction
    str_reversed =''.join(reversed(scolon_left))

    # Define special characters to search for
    characters = ['(', ')', " ", '+', "-","*","/","^", "'"]

    # Find the first instance of a special character
    finds = []
    for character in characters:

        finds.append(str_reversed.find(character))

    # Remove -1 from list
    finds = list(filter(lambda a: a != -1, finds))

    # Get everything up to the first special character
    if finds:
        mystr = str_reversed[0:min(finds)]
    else:
        mystr = str_reversed

    # Reverse to return to normal order
    compound =''.join(reversed(mystr))


    # Find everything right of the semicolon
    scolon_right = my_string[scolon:]

    # Find the first instance of a special character
    finds = []
    for character in characters:

        finds.append(scolon_right.find(character))

    # Remove -1 from list
    finds = list(filter(lambda a: a != -1, finds))

    if finds:
        block_param = scolon_right[:min(finds)]
    else:
        block_param = scolon_right

    scp_key = compound + block_param

    return scp_key

# ------------/ Create dataframe from uploaded file /--------------
def parse_contents(contents, filename, date):
    content_type, content_string = contents.split(',')

    decoded = base64.b64decode(content_string)
    try:
        if 'csv' in filename:
            # Assume that the user uploaded a CSV file
            df = pd.read_csv( io.StringIO(decoded.decode('utf-8')), index_col=None, skiprows=1)
        elif 'xls' in filename:
            # Assume that the user uploaded an excel file
            df = pd.read_excel(io.BytesIO(decoded))

    except Exception as e:
        print(e)
        return html.Div([
            'There was an error processing this file.'
        ])
    
    return df

# ------------/ Create Dash Table from uploaded file /--------------
def parse_contents_table(df, title):
    return html.Div([

        # Table Title
        html.H5(title),

        # Dash Table
        dash_table.DataTable(
            data=df.to_dict('records'),
            columns=[{'name': i, 'id': i} for i in df.columns]
        ),

        # horizontal line
        html.Hr(),  
    ])


# ---------------------------------------
# -----------/ App Seteup /--------------
# ---------------------------------------

about_text1 = """
Use this to create unique keys for Dynsim cross reference files.

Unique keys are added to the MISC5 column of the cross reference file, which enables easier cross reference merging and manipulation
"""
about_text3 = 'Try it!'


# external JavaScript files
external_scripts = [
    {
        'src': 'https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.14.7/umd/popper.min.js',
        'integrity': 'sha384-UO2eT0CpHqdSJQ6hJty5KVphtPhzWj9WO1clHTMGa3JDZwrnQq4sF86dIHNDz0W1',
        'crossorigin': 'anonymous'
    },
    {
        'src': 'https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/js/bootstrap.min.js',
        'integrity': 'sha384-JjSmVgyd0p3pXB1rRibZUAYoIIy6OrQ6VrjIEaFf/nJGzIxFDsf4x0xIM+B07jRM',
        'crossorigin': 'anonymous'
    },
    'https://codepen.io/chriddyp/pen/bWLwgP.css',
    "d3.v5.min.js",
    "download.js",
    "static.js",
]

server = flask.Flask(__name__)
# server.secret_key = os.environ.get('secret_key', str(randint(0, 1000000)))
app = dash.Dash(__name__, 
                server=server)

app.title = "Dynsim Xref Tool"

colors = {
    'background': "#111111",
    'text': '#7FDBFF'
}


# ---------------------------------------
# -----------/ App Layout /--------------
# ---------------------------------------
app.layout = html.Div(children=[

    # ------------/ Feedback Popup /--------------  
    html.Div([
            dbc.Modal(
                [
                    dbc.ModalHeader("Your Feedback Is Important"),
                    dbc.ModalBody(
                        html.Div([
                            
                            html.P("How can this tool be more useful to you?"),
                            dcc.Textarea(
                                placeholder='Type here...',
                                value='',
                                style={'width': '100%'},
                                id ="user-comment"
                            )
                            ]),       
                    ),
                    dbc.ModalFooter(
                        dbc.Button("Submit", id="close", className="ml-auto")
                    ),
                ],
                id="modal",
                size="lg"
            ),
        ]), 

    # ------------/ Begin Bootstrap Container /--------------  
    html.Div([

        # ------------/ Introduction /--------------   
        html.Div([
            html.H1(
                    children='Dynsim Xref Tool',
                )
            ], className='row justify-content-center'),

        # ------------/ Introduction 2 /--------------
        html.Div([
            html.Div(
                    children= [html.Br(), 
                        html.H4("Use this to create unique keys for Dynsim cross reference files."),
                        html.Br(), 
                        html.H4("Unique keys are added to the MISC5 column of the cross reference file, which enables easier cross reference merging and manipulation."),
                        html.Br()
                        ],
                    className="lg-col-12",
                    style={
                        'textAlign': 'left'
                    }
                ),
        ], className='row'),

        # ------------/ Upload / Interact / Download /--------------
        html.Div([

            # ------------/ Upload  /--------------
            html.Div([
                dcc.Upload(
                    id='upload-data',
                    children=html.Div([
                        'Try It! 1.  Drag and Drop or ',
                        html.A(['Select a Xref File'], style = {"color": "#007BFF"})
                    ]),
                    style={
                        'width': '100%',
                        'height': '60px',
                        'lineHeight': '60px',
                        'borderWidth': '1px',
                        'borderStyle': 'dashed',
                        'borderRadius': '5px',
                        'textAlign': 'center',
                        'margin': '10px',
                    },
                    # Do not allow multiple files to be uploaded
                    multiple=False
                ),
            ], style = {"width": "33%", "display":"inline-block","position":"relative", 'textAlign': 'right'}, className='justify-content-center'),

            # ------------/ Interact  /--------------
            html.Div([
                html.H6('2.  Enter Your SCP Engine Names Below'), 
                ], style = {"width": "33%", "display":"inline-block","position":"relative",'textAlign': 'center'}),

            # ------------/ Download  /--------------
            html.Div([
                html.A('3.  Download Your Improved Xref', href='#', id='download-button')
            ], style = {"width": "34%", "display":"inline-block","position":"relative",'textAlign': 'left'}),
        ]),

        # ------------/ Information /--------------
        html.P(children=[html.Br()]),

        html.Div([
            html.H4(
                    children='Select SCP Engine Names',
                )
        ], className='row justify-content-center'),

        # ------------/ Dropdown /--------------
        html.Div([
            html.Div([], style = {"width": "33%", "display":"inline-block","position":"relative"}),
            html.Div([
                dcc.Dropdown(
                    id='fit-dropdown',
                    value='',
                    clearable=False,
                    multi=True
                ),
                ], style = {"width": "34%", "display":"inline-block","position":"relative"}),
            html.Div([], style = {"width": "33%", "display":"inline-block","position":"relative"}),
        ]),

        # ------------/ Number of keys generated /--------------
        #html.P(children=[html.Br(),html.Br()]),
        html.Div(id='file-title', style={'textAlign': 'center'}),
        html.Div(id='key-count', style={'textAlign': 'center'}),

        # ------------/ Analogs Table /--------------
        #html.P(children=[html.Br(),html.Br()]),
        html.Div(id='a-xref'),

        # ------------/ Digitals Table /--------------
        #html.P(children=[html.Br(),html.Br()]),
        html.Div(id='d-xref'),

        # ------------/ Feedback Button /--------------
        dbc.Button("Request A New Feature / Make a Complaint", id="open"),

        # Hidden div inside the app that stores the data uploaded by the user
        html.Div(id='uploaded-json', style={'display': 'none'}),

        # Hidden div inside the app that stores the improved analog crossref
        html.Div(id='new-a-xref-csv', style={'display': 'none'}),

        # Hidden div inside the app that stores the improved digital crossref
        html.Div(id='new-d-xref-csv', style={'display': 'none'}),

        # Hidden div inside the app that stores the improved analog crossref
        html.Div(id='downloadable-csv', style={'display': 'none'}),

        # Hidden div inside the app that stores comments
        html.Div(id='placeholder', style={'display': 'none'})


   ], className='container')

])

# ---------------------------------------
# -----------/ Callbacks /--------------
# ---------------------------------------

#-------/ Data Uploaded or contraints changed / -----------------
# display the data that the user has uploaded in a table, and store data that the user uploaded into a hidden div, and update x/y sliders settings
@app.callback([Output('uploaded-json', 'children'),
                Output('new-a-xref-csv', 'children'),
                Output('new-d-xref-csv', 'children'),
                Output('fit-dropdown', "options"),
                Output('fit-dropdown', "value"),
                Output('file-title', "children")],
              [Input('upload-data', 'contents')],
              [State('upload-data', 'filename'),
               State('upload-data', 'last_modified')])
def update_output(contents, filename, last_modified):
    
    # if there are contents in the upload
    if contents is not None:

        # Use the contents to create a dataframe
        upload_df = parse_contents(contents, filename, last_modified)

        values = []
    
    # On intial page load, or failure, use example data
    else:
        upload_df = pd.read_csv('Resources/design_data.csv', index_col=None, skiprows=1)

        # for example, load the correct engines
        values = ['ExampleSCP1', 'ExampleSCP2']

        filename = "Example_Xref.csv"

    engine_list = get_engines(upload_df)

    options=[{'label': engine, 'value': engine} for engine in engine_list]

    # Split user df to analogs and digitals
    a_df, d_df = split_xref(upload_df)
    
    return (upload_df.to_json(date_format='iso', orient='split'),
            a_df.to_json(date_format='iso', orient='split'),
            d_df.to_json(date_format='iso', orient='split'),
            options,
            values,
            html.H6(filename))
            

#-------/ Engine Names Selected / Data Uploaded / -----------------
@app.callback([ Output('a-xref', 'children'),
                Output('d-xref', 'children'),
                Output('key-count', 'children'),
                Output('downloadable-csv', 'children')],
              [Input('fit-dropdown', 'value')], 
              [State('new-a-xref-csv', 'children'),
              State('new-d-xref-csv', 'children')]
              )
def update_tables(selection, a_jsonified, d_jsonified):
    
    if (a_jsonified is not None and d_jsonified is not None):

        # Read contents of hidden div
        a_df = pd.read_json(a_jsonified, orient='split')
        d_df = pd.read_json(d_jsonified, orient='split')

        # Add the SCP to MISC 5
        a_df, a_key_count = get_scp_field(a_df, selection)
        d_df, d_key_count = get_scp_field(d_df, selection)
        
        # Show the user the first five rows of selected columns of the df
        a_view_df = a_df[["#TYPE", "FROM ENGINE", "EQUATION", "MISC5"]].iloc[:5]
        d_view_df = d_df[["#TYPE", "FROM ENGINE", "EQUATION", "MISC5"]].iloc[:5]

        a_view_children = parse_contents_table(a_view_df, "Analogs Preview")
        d_view_children = parse_contents_table(d_view_df, "Digitals Preview")

        return a_view_children, d_view_children, html.H6(f"{str(a_key_count + d_key_count)} Keys Generated"), "SIM4ME\n" + a_df.to_csv(index=False) + d_df.to_csv(index=False)
    
    else:

        return "", "", "", ""


#-------/ Open feedback form / -----------------
@app.callback(
    Output("modal", "is_open"),
    [Input("close", "n_clicks"), Input("download-button", "n_clicks"), Input("open", "n_clicks")],
    [State("modal", "is_open")],
)
def toggle_modal(close_clicks, download_clicks, open_click, is_open):
    
    if download_clicks or open_click:
        
        if close_clicks:

            return not is_open

        return not is_open

    return False


#-------/ Add feedback to feedback list / -----------------
@app.callback(
    Output("placeholder", "children"),
    [Input("modal", "is_open")],
    [State("user-comment", "value")]
)
def update_comments(n_clicks, string):

    if string:

        comments_df = pd.read_csv("Resources/comments.csv")
        comment_list = comments_df["comment"].to_list()
        comment_list.append(string)
        comments_df = pd.DataFrame(data = {"comment" : comment_list})
        comments_df.to_csv("Resources/comments.csv")

        return comments_df.to_json(date_format='iso', orient='split')
    
    return ""


if __name__=='__main__':
    app.run_server(debug=True)
    # app.run_server(dev_tools_hot_reload=False)