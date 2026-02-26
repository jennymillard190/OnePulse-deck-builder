"""
Chart creation helpers for Streamlit UI.
Consolidates duplicate chart creation code.
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd


def create_grouped_bar_chart(df_display: pd.DataFrame, title: str, key_prefix: str):
    """
    Create a grouped bar chart from a DataFrame.
    
    Args:
        df_display: DataFrame with 'Category' column and value columns
        title: Title for the chart (used in key)
        key_prefix: Prefix for the unique Streamlit key
    """
    df_indexed = df_display.set_index('Category')
    fig = go.Figure()
    for col in df_indexed.columns:
        fig.add_trace(go.Bar(
            name=col,
            x=df_indexed.index,
            y=df_indexed[col],
            text=[f"{v:.1%}" if v < 1 else f"{v:.0f}" for v in df_indexed[col]],
            textposition='auto',
            hovertemplate=f'<b>%{{x}}</b><br>{col}: %{{y}}<extra></extra>'
        ))
    fig.update_layout(
        barmode='group',
        height=400,
        xaxis_title="Category",
        yaxis_title="Value",
        dragmode=False,
        showlegend=True
    )
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    plotly_config = {'scrollZoom': False, 'displayModeBar': True}
    st.plotly_chart(fig, width='stretch', config=plotly_config, key=f"{key_prefix}_{title}")


def create_category_distribution_chart(chart_data: pd.DataFrame):
    """
    Create a simple bar chart showing category distribution percentages.
    
    Args:
        chart_data: DataFrame with 'Category' and 'Percentage' columns
    """
    fig = go.Figure(data=[
        go.Bar(
            x=chart_data["Category"],
            y=chart_data["Percentage"],
            text=[f"{p}%" for p in chart_data["Percentage"]],
            textposition='auto',
            hovertemplate='<b>%{x}</b><br>Percentage: %{y:.1f}%<extra></extra>'
        )
    ])
    fig.update_layout(
        height=700,
        xaxis_title="Category",
        yaxis_title="Percentage (%)",
        dragmode=False,
        showlegend=False
    )
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    
    plotly_config = {'scrollZoom': False, 'displayModeBar': True}
    st.plotly_chart(fig, width='stretch', config=plotly_config, key="category_distribution_chart")


def create_stacked_breakdown_chart(chart_df: pd.DataFrame, breakdown_values: list, index_data: dict):
    """
    Create a stacked bar chart with breakdown values and index data.
    
    Args:
        chart_df: DataFrame with 'Category' column and columns for each breakdown value
        breakdown_values: List of breakdown value names
        index_data: Dict mapping breakdown values to lists of index values
    """
    fig = go.Figure()
    for breakdown_value in breakdown_values:
        # Create text with percentage and index
        text_labels = []
        for i, p in enumerate(chart_df[breakdown_value]):
            if p > 0:
                index_val = index_data[breakdown_value][i]
                if index_val is not None:
                    text_labels.append(f"{p}%<br>Index: {int(index_val)}")
                else:
                    text_labels.append(f"{p}%")
            else:
                text_labels.append("")
        
        fig.add_trace(go.Bar(
            name=breakdown_value,
            x=chart_df["Category"],
            y=chart_df[breakdown_value],
            text=text_labels,
            textposition='inside',
            hovertemplate=f'<b>%{{x}}</b><br>{breakdown_value}: %{{y:.1f}}%<br>Index: %{{customdata}}<extra></extra>',
            customdata=[int(idx) if idx is not None else 0 for idx in index_data[breakdown_value]]
        ))
    fig.update_layout(
        barmode='stack',
        height=700,
        xaxis_title="Category",
        yaxis_title="Percentage (%)",
        dragmode=False,
        showlegend=True
    )
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    
    plotly_config = {'scrollZoom': False, 'displayModeBar': True}
    st.plotly_chart(fig, width='stretch', config=plotly_config, key="breakdown_chart")
