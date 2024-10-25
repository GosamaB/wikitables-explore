from flask import Flask, render_template, request
import pandas as pd
import ast

file_path = '../wikitables.csv'
data = pd.read_csv(file_path, encoding='utf-8')

def parse_table(schema, data):
    columns = ast.literal_eval(schema)
    data_list = ast.literal_eval(data)

    rows = []
    for row in data_list:
        row_values = [entry[0] for entry in row]
        rows.append(row_values)
    
    return pd.DataFrame(rows, columns=columns)

parsed_tables = []

for index, row in data.iterrows():
    parsed_df = parse_table(row['schema'], row['data'])
    if not parsed_df.empty:
        parsed_tables.append({row['title']: parsed_df})

app = Flask(__name__)

def remove_invalid_characters(text):
    return text.encode('utf-8', 'surrogatepass').decode('utf-8', 'ignore')

ROWS_PER_PAGE = 15
TABLES_PER_PAGE = 5

@app.route('/')
def index():
    table_set_page = int(request.args.get('table_set_page', 1))
    search_query = request.args.get('search', '').lower()

    if search_query:
        filtered_tables = []
        for table_dict in parsed_tables:
            for title, table in table_dict.items():
                if search_query in title.lower() or any(search_query in col.lower() for col in table.columns):
                    filtered_tables.append({title: table})
    else:
        filtered_tables = parsed_tables

    start_table = (table_set_page - 1) * TABLES_PER_PAGE
    end_table = start_table + TABLES_PER_PAGE
    table_set = filtered_tables[start_table:end_table]

    cleaned_table_set = []
    for table_dict in table_set:
        for title, table in table_dict.items():
            cleaned_table = table.applymap(lambda x: remove_invalid_characters(str(x)))
            cleaned_table_set.append({title: cleaned_table})

    total_table_sets = (len(filtered_tables) // TABLES_PER_PAGE) + (1 if len(filtered_tables) % TABLES_PER_PAGE else 0)

    return render_template('index.html', 
                           table_set=cleaned_table_set, 
                           table_set_page=table_set_page,
                           total_table_sets=total_table_sets,
                           search_query=search_query)

df = pd.read_csv('../schema_auto_complete_results.csv')

RESULTS_PER_PAGE = 5

@app.route('/compare-schemas', methods=['GET'])
def compare_schemas():
    search_query = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)

    if search_query:
        filtered_df = df[df['title'].str.contains(search_query, case=False, na=False)]
    else:
        filtered_df = df

    total_records = len(filtered_df)
    total_pages = (total_records - 1) // RESULTS_PER_PAGE + 1
    start = (page - 1) * RESULTS_PER_PAGE
    end = start + RESULTS_PER_PAGE
    paginated_df = filtered_df.iloc[start:end]

    comparison_results = []
    for index, row in paginated_df.iterrows():
        schema_sorted = sorted(ast.literal_eval(row['schema']))
        out_schema_sorted = sorted(ast.literal_eval(row['out_schema']))
        pairs_sorted = sorted([t[0] for t in ast.literal_eval(row['matching_pairs'])])
        out_pairs_sorted = sorted([t[1] for t in ast.literal_eval(row['matching_pairs'])])

        matched_columns = list(sorted(ast.literal_eval(row['matching_pairs']), key=lambda x: x[0]))
        unmatched_in_schema = list(set(schema_sorted) - set(pairs_sorted))
        unmatched_in_out_schema = list(set(out_schema_sorted) - set(out_pairs_sorted))

        total_columns = len(set(schema_sorted + out_schema_sorted))

        comparison_results.append({
            'title': row['title'],
            'matched_columns': matched_columns,
            'unmatched_in_schema': unmatched_in_schema,
            'unmatched_in_out_schema': unmatched_in_out_schema,
            'schema_sorted': schema_sorted,
            'out_schema_sorted': out_schema_sorted,
            'accuracy': row['accuracy'] * 100,
        })

    return render_template(
        'compare-schemas.html',
        comparison_results=comparison_results,
        page=page,
        total_pages=total_pages,
        search_query=search_query
    )

if __name__ == '__main__':
    app.run(debug=True)