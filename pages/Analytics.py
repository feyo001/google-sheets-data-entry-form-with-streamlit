import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import numpy as np
import altair as alt
# import plotly.express as px



# Display Title and Description
st.title("Sales Management Portal")
st.html("styles.html")  # Assuming styles.html contains styling information

# Establishing a Google Sheets connection
conn = st.connection("gsheets", type=GSheetsConnection)

# Function to get data from a specific sheet (using cache for efficiency)
@st.cache_data(ttl=5)
def get_sheet_data(sheet_name):
    return conn.read(worksheet=sheet_name, usecols=list(range(5))).dropna(how='all')

# Function to wrangle data
def data_wrangle(data):
    data['DATE'] = pd.to_datetime(data['DATE'], format='%m/%d/%Y')
    data['MONTH'] = data['DATE'].dt.month
    # data['WEEK'] = pd.to_datetime(data['DATE']).dt.to_period('W').apply(lambda a: a.start_time)
    data['WEEK'] = data['DATE'].dt.isocalendar().week
    data['PRICE'] = pd.to_numeric(data['PRICE'], errors='coerce').fillna(0)
    data['UNITS'] = pd.to_numeric(data['UNITS'], errors='coerce').fillna(0)
    return data

# Fetch and process data
sales_df = get_sheet_data("Sales")

def expences_data_wrangle(data):
    # data = get_sheet_data("Expenses")
    data['Date'] = pd.to_datetime(data['Date'], format='%d/%m/%Y')
    data['Month'] = data['Date'].dt.month
    data['Item'] = data['Item'].str.strip()
    data['Description'] = data['Description'].str.strip()

    return data

# Get the expenses table
expenses = get_sheet_data("Expenses")
expenses_df= expences_data_wrangle(expenses)
# st.dataframe(expenses_df)

sales_display_table = None
df = data_wrangle(sales_df)

# Month dictionary for selection
month_dict = {
    1 : "January", 2 : "February", 3: "March", 4 : "April", 5:"May", 6:"June",
    7:"July", 8:"August", 9:"September", 10:"October", 11:"November", 12:"December",
}



# Single container for date selection and metrics display
container = st.container()
left_widget, right_indicator = st.columns([1.5,1.8])

with container:
    with left_widget:
        selected_date = st.date_input("Select Date")

        monthly_sales_df = df.query("MONTH == @selected_date.month")
        monthly_expenses_df = expenses_df.query("Month == @selected_date.month")

        # Filter data by month or date (based on selection)
        if selected_date is not None:
            if selected_date.month == st.session_state.get('prev_month', None):
                filtered_df = df.query("DATE == @selected_date")
                sales_display_table = filtered_df
                filtered_expense_df = expenses_df.query("Date == @selected_date")
                st.subheader("Daily Metrics")
            else:
                # pass
                filtered_df = df.query("MONTH == @selected_date.month")                                
                filtered_expense_df = expenses_df.query("Month == @selected_date.month")
                st.session_state['prev_month'] = selected_date.month
                st.subheader("Overall Month Metrics")       

        else:
            filtered_df = pd.DataFrame()  # Empty DataFrame if no date selected
            expenses_df = pd.DateFrame()

        @st.experimental_fragment
        def display_metrics(df, title):
            """
            Calculates and displays metrics for a given DataFrame with a title.
            """
            total_sales = df['PRICE'].sum()
            total_products = df['NAME'].nunique()
            average_sales = df['PRICE'].mean()
            # total_expenses = filtered_expense_df['Amount'].sum()
            total_expenses = filtered_expense_df.query('~(Item == "Pepvic Ventures" or Item == "Weekly Contribution(Mama)")')['Amount'].sum()
            
            pepvic_contributon = filtered_expense_df.query('Item == "Pepvic Ventures"')['Amount'].sum()
            weekly_contribution = filtered_expense_df.query('Item == "Weekly Contribution(Mama)"')['Amount'].sum()

            #######################################################
            total_sales_by_month = monthly_sales_df['PRICE'].sum()
            total_expenses_by_month = monthly_expenses_df['Amount'].sum()

            st.metric("Total Sales by Month", value=f"₦{total_sales_by_month:,.0f}", delta=f"{title} Sales")
            st.metric("Total Expenses by Month", value=f"₦{total_expenses_by_month:,.0f}", delta=f"{title} Expenses")
            #######################################################

            # Use st.columns for side-by-side metrics (optional)
            col1, col2 = right_indicator.columns([1.2, 1.1])
            with col1:
                st.html('<span class="high_indicator"></span>')  # Assuming class for styling
                st.metric("Total Sales (Daily)", value=f"₦{total_sales:,.0f}", delta=f"{title} Sales")
                st.metric("Total Products", value=total_products, delta=f"{title} Volume")
                st.metric("Average Sales", value=f"₦{0 if average_sales is np.nan else average_sales:,.0f}", delta=f"{title} Avg. Sales")
                
            with col2:
                st.html('<span class="low_indicator"></span>')  # Assuming class for styling
                st.metric("Pepvic Ventures", value=f"₦{pepvic_contributon:,.0f}", delta=f"{title} Pepvic Ventures")
                st.metric("Weekly Contribution", value=f"₦{weekly_contribution:,.0f}", delta=f"{title} Weekly Contribution")
                st.metric("Daily Expenses", value=f"₦{total_expenses:,.0f}", delta=f"{title} Expenses")

            # with col3:
            #     st.html('<span class="bottom_indicator"></span>')
                

        if not filtered_df.empty:
            display_metrics(filtered_df, title="")  # No title needed for dynamic updates



with st.container():
    top_products_sold_by_amount = (
        filtered_df.groupby(['NAME'])['PRICE']
        .sum()
        .sort_values(ascending=False)
        .reset_index()
        .head(5)
    )
    
    # Ensure no missing values (vectorized)
    top_products_sold_by_amount = top_products_sold_by_amount.fillna({
        'NAME': 'Unknown',
        'PRICE': 0
    })

    # Creating the Altair chart with professional formatting (using chaining)
    chart = (
        alt.Chart(top_products_sold_by_amount)
        .mark_bar(color='#3182bd')
        .encode(
            x=alt.X('NAME:N', sort=None, title='Product', axis=alt.Axis(labelAngle=45)),
            y=alt.Y('PRICE:Q', title='Total Value'),
            tooltip=[alt.Tooltip('NAME:N', title='Product'), alt.Tooltip('PRICE:Q', title='Total Value')]
        )
        .properties(
            title='Top 5 Selling Products',
            width=alt.Step(40)
        )
        .configure_title(
            fontSize=20,
            font='Arial',
            color='#333'
        )
        .configure_axis(
            titleFontSize=16,
            labelFontSize=12
        )
        .configure_view(
            strokeWidth=0
        )
    )

    # Displaying the chart
    st.altair_chart(chart, use_container_width=True)

    # st.dataframe(filtered_df)

    # line_chart_df = filtered_df.dropna(axis=1)
    # temp = df.query("DATE == @selected_date")
    # temp = sales_df.query('DATE == @date.month')
    # st.write(temp)  # Optional for debugging
    # st.write(selected_date.month)

    
    st.write(f"You selected data for month: {month_dict[selected_date.month]}")
   

    # Assuming 'DATE' is a datetime column (adjust if needed)
filtered_sales_data = (
    sales_df.groupby("DATE")["PRICE"]
    .sum()
    .reset_index()
    .query("DATE.dt.month == @selected_date.month")
)

# Display data (optional)
sales_display_table['DATE']=sales_display_table['DATE'].dt.date
sales_display_table = sales_display_table[['DATE','NAME','UNITS','PRICE']].sort_index(ascending=True).reset_index(drop=True)

st.write(sales_display_table[['DATE','NAME','UNITS','PRICE']])

# Create the chart with Altair
line_chart = (
    alt.Chart(filtered_sales_data)
    .mark_line(color="blue")
    .encode(
        x=alt.X("DATE:T", axis=alt.Axis(title="Date")),
        y=alt.Y("PRICE:Q", axis=alt.Axis(title="Price (Sum)")),
    )
    .properties(width=800, height=400)  # Adjust width and height as needed
)

# Display the chart using Streamlit
st.altair_chart(line_chart, use_container_width=True)




# # # Top 5 Total units sold per products
# # st.subheader("Top 5 products by units sold")
# # units_per_products1 = (filtered_df
# #     .groupby(['NAME'])['UNITS']
# #     .sum()
# #     .sort_values(ascending=False)
# #     .reset_index()
# #     .head(5))

# # with st.expander("Products by Units"):
# #     # st.dataframe(units_per_products1)
# #     chart_units_per_products1 = (
# #         alt.Chart(units_per_products1)
# #         .mark_bar(color='#3182bd')
# #         .encode(
# #             x=alt.X('NAME:N', sort=None, title='Product', axis=alt.Axis(labelAngle=45)),
# #             y=alt.Y('UNITS:Q', title='Total Units'),
# #             text=alt.Text('UNITS:Q'),  # Add text encoding for value display
# #             # text=alt.Text('UNITS:Q', dy=-5),
# #             tooltip=[alt.Tooltip('NAME:N', title='Product'), alt.Tooltip('UNITS:Q', title='Total Units')]
# #         )
# #         .properties(
# #             title='Top Products by Units',
# #             width=alt.Step(40)
# #         )
# #         .configure_title(
# #             fontSize=20,
# #             font='Arial',
# #             color='#333'
# #         )
# #         .configure_axis(
# #             titleFontSize=16,
# #             labelFontSize=12
# #         )
# #         .configure_view(
# #             strokeWidth=0
# #         )
# #     )
# #     # Displaying the chart
# #     st.altair_chart(chart_units_per_products1, use_container_width=True)


# # # Least 5 Total units sold per products
# # # st.subheader("Least 5 products by units sold")
# # # units_per_products2 = (
# # #     filtered_df.groupby(['NAME'])['UNITS']
# # #     .sum()
# # #     .sort_values(ascending=False)
# # #     .reset_index()
# # #     .tail(5))
# # # st.dataframe(units_per_products2)






