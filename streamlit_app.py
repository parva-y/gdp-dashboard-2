import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Marketing Funnel Analyzer", layout="wide", page_icon="📊")

st.title("📊 Marketing Funnel Impact Analyzer")
st.markdown("Upload your iOS, Android, and Media Spend data to analyze funnel performance")

# File uploaders
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("📱 iOS App Data")
    ios_file = st.file_uploader("Upload iOS CSV", type=['csv'], key='ios')

with col2:
    st.subheader("🤖 Android App Data")
    android_file = st.file_uploader("Upload Android CSV", type=['csv'], key='android')

with col3:
    st.subheader("💰 Media Spends")
    spend_file = st.file_uploader("Upload Spends CSV", type=['csv'], key='spend')

def safe_read_csv(f):
    # read csv, strip column names
    df = pd.read_csv(f)
    df.columns = df.columns.str.strip()
    return df

def parse_date_col(df):
    # find a date-like column and convert to datetime robustly
    possible_date_cols = [c for c in df.columns if 'date' in c.lower()]
    if not possible_date_cols:
        return None, None
    col = possible_date_cols[0]
    df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=False)
    return col, df

if ios_file and android_file and spend_file:
    try:
        # Read
        ios_df = safe_read_csv(ios_file)
        android_df = safe_read_csv(android_file)
        spend_df = safe_read_csv(spend_file)

        # Parse dates (robustly)
        ios_date_col, ios_df = parse_date_col(ios_df)
        android_date_col, android_df = parse_date_col(android_df)
        spend_date_col, spend_df = parse_date_col(spend_df)

        if ios_date_col is None or android_date_col is None or spend_date_col is None:
            st.error("Couldn't find a Date column in one of the files. Make sure each CSV has a Date column.")
            st.stop()

        # Normalize date column name
        ios_df = ios_df.rename(columns={ios_date_col: 'Date'})
        android_df = android_df.rename(columns={android_date_col: 'Date'})
        spend_df = spend_df.rename(columns={spend_date_col: 'Date'})

        # Drop rows with invalid dates
        ios_df = ios_df.dropna(subset=['Date'])
        android_df = android_df.dropna(subset=['Date'])
        spend_df = spend_df.dropna(subset=['Date'])

        # Prefix platform columns so we can merge safely
        ios_df = ios_df.add_prefix('ios_').rename(columns={'ios_Date': 'Date'})
        android_df = android_df.add_prefix('android_').rename(columns={'android_Date': 'Date'})

        # Normalize spend column name in spends file (common variations)
        spend_col_candidates = [c for c in spend_df.columns if any(k in c.lower() for k in ('spend','spends','amount','cost','media'))]
        if spend_col_candidates:
            spend_col = spend_col_candidates[0]
            spend_df = spend_df.rename(columns={spend_col: 'Spends'})
        else:
            # if nothing found create column
            spend_df['Spends'] = 0

        # Ensure Date is datetime and round to day
        for df in (ios_df, android_df, spend_df):
            df['Date'] = pd.to_datetime(df['Date']).dt.normalize()

        # Merge outer on Date
        combined_df = pd.merge(ios_df, android_df, on='Date', how='outer')
        combined_df = pd.merge(combined_df, spend_df, on='Date', how='outer')

        # Sort and fill missing numeric columns with 0
        combined_df = combined_df.sort_values('Date').reset_index(drop=True)
        combined_df = combined_df.fillna(0)

        # Helper: sum any columns matching a regex (per-row)
        def sum_cols_by_regex(df, pattern):
            cols = [c for c in df.columns if pattern.lower() in c.lower()]
            if not cols:
                return pd.Series(0, index=df.index)
            return df[cols].select_dtypes(include=[np.number]).sum(axis=1)

        # Platform installs / kyc / otp (robust to many column name variants)
        combined_df['ios_installs'] = sum_cols_by_regex(combined_df, 'ios') * 0  # placeholder
        # more robust filters:
        combined_df['ios_installs'] = combined_df[[c for c in combined_df.columns if c.lower().startswith('ios') and 'install' in c.lower()]].sum(axis=1) if any(c.lower().startswith('ios') and 'install' in c.lower() for c in combined_df.columns) else pd.Series(0, index=combined_df.index)
        combined_df['android_installs'] = combined_df[[c for c in combined_df.columns if c.lower().startswith('android') and 'install' in c.lower()]].sum(axis=1) if any(c.lower().startswith('android') and 'install' in c.lower() for c in combined_df.columns) else pd.Series(0, index=combined_df.index)

        combined_df['ios_kyc'] = combined_df[[c for c in combined_df.columns if c.lower().startswith('ios') and 'kyc' in c.lower()]].sum(axis=1) if any(c.lower().startswith('ios') and 'kyc' in c.lower() for c in combined_df.columns) else pd.Series(0, index=combined_df.index)
        combined_df['android_kyc'] = combined_df[[c for c in combined_df.columns if c.lower().startswith('android') and 'kyc' in c.lower()]].sum(axis=1) if any(c.lower().startswith('android') and 'kyc' in c.lower() for c in combined_df.columns) else pd.Series(0, index=combined_df.index)

        combined_df['ios_otp'] = combined_df[[c for c in combined_df.columns if c.lower().startswith('ios') and 'otp' in c.lower()]].sum(axis=1) if any(c.lower().startswith('ios') and 'otp' in c.lower() for c in combined_df.columns) else pd.Series(0, index=combined_df.index)
        combined_df['android_otp'] = combined_df[[c for c in combined_df.columns if c.lower().startswith('android') and 'otp' in c.lower()]].sum(axis=1) if any(c.lower().startswith('android') and 'otp' in c.lower() for c in combined_df.columns) else pd.Series(0, index=combined_df.index)

        # totals
        combined_df['total_installs'] = combined_df['ios_installs'] + combined_df['android_installs']
        combined_df['total_kyc'] = combined_df['ios_kyc'] + combined_df['android_kyc']
        combined_df['total_otp'] = combined_df['ios_otp'] + combined_df['android_otp']

        # Spends numeric
        if 'Spends' not in combined_df.columns:
            combined_df['Spends'] = 0
        combined_df['Spends'] = pd.to_numeric(combined_df['Spends'], errors='coerce').fillna(0)

        # Conversion rates (safe: avoid division by zero)
        combined_df['install_to_kyc'] = np.where(combined_df['total_installs'] > 0,
                                                 combined_df['total_kyc'] / combined_df['total_installs'] * 100,
                                                 0)
        combined_df['install_to_otp'] = np.where(combined_df['total_installs'] > 0,
                                                 combined_df['total_otp'] / combined_df['total_installs'] * 100,
                                                 0)
        combined_df['kyc_to_otp'] = np.where(combined_df['total_kyc'] > 0,
                                             combined_df['total_otp'] / combined_df['total_kyc'] * 100,
                                             0)

        # CPI (safe)
        combined_df['cpi'] = np.where(combined_df['total_installs'] > 0,
                                      combined_df['Spends'] / combined_df['total_installs'],
                                      np.nan)  # use nan so we can ignore days with zero installs

        # Summary Metrics
        st.markdown("---")
        st.header("📈 Key Performance Metrics")

        total_spend = combined_df['Spends'].sum()
        total_installs = combined_df['total_installs'].sum()
        total_kyc = combined_df['total_kyc'].sum()
        total_otp = combined_df['total_otp'].sum()
        avg_cpi = (total_spend / total_installs) if total_installs > 0 else 0

        metric_col1, metric_col2, metric_col3, metric_col4, metric_col5 = st.columns(5)

        with metric_col1:
            st.metric("Total Spend", f"₹{total_spend:,.0f}")
        with metric_col2:
            st.metric("Total Installs", f"{total_installs:,.0f}")
        with metric_col3:
            st.metric("Avg CPI", f"₹{avg_cpi:.2f}")
        with metric_col4:
            install_to_kyc_pct = (total_kyc / total_installs * 100) if total_installs > 0 else 0
            st.metric("Install → KYC", f"{install_to_kyc_pct:.1f}%")
        with metric_col5:
            install_to_otp_pct = (total_otp / total_installs * 100) if total_installs > 0 else 0
            st.metric("Install → OTP", f"{install_to_otp_pct:.1f}%")

        # Visualizations
        st.markdown("---")
        st.header("📊 Impact Analysis")

        # 1. Spend vs Installs
        fig1 = make_subplots(specs=[[{"secondary_y": True}]])

        fig1.add_trace(
            go.Bar(x=combined_df['Date'], y=combined_df['Spends'], name="Media Spend"),
            secondary_y=False,
        )

        fig1.add_trace(
            go.Scatter(x=combined_df['Date'], y=combined_df['total_installs'],
                       name="Total Installs", mode='lines+markers'),
            secondary_y=True,
        )

        fig1.update_xaxes(title_text="Date")
        fig1.update_yaxes(title_text="Media Spend (₹)", secondary_y=False)
        fig1.update_yaxes(title_text="Installs", secondary_y=True)
        fig1.update_layout(title="Media Spend Impact on Installs", height=400)

        st.plotly_chart(fig1, use_container_width=True)

        # 2. Funnel Analysis
        col_a, col_b = st.columns(2)

        with col_a:
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=combined_df['Date'], y=combined_df['total_installs'],
                                      name='Installs', mode='lines+markers'))
            fig2.add_trace(go.Scatter(x=combined_df['Date'], y=combined_df['total_kyc'],
                                      name='KYC Completed', mode='lines+markers'))
            fig2.add_trace(go.Scatter(x=combined_df['Date'], y=combined_df['total_otp'],
                                      name='Mobile OTP', mode='lines+markers'))
            fig2.update_layout(title="Funnel Progression Over Time", height=400)
            st.plotly_chart(fig2, use_container_width=True)

        with col_b:
            fig3 = go.Figure()
            fig3.add_trace(go.Scatter(x=combined_df['Date'], y=combined_df['install_to_kyc'],
                                      name='Install → KYC %', mode='lines+markers'))
            fig3.add_trace(go.Scatter(x=combined_df['Date'], y=combined_df['install_to_otp'],
                                      name='Install → OTP %', mode='lines+markers'))
            fig3.update_layout(title="Conversion Rates Over Time", yaxis_title="Conversion %", height=400)
            st.plotly_chart(fig3, use_container_width=True)

        # 3. Platform Comparison
        st.markdown("---")
        st.header("🔄 Platform Comparison")

        col_c, col_d = st.columns(2)

        with col_c:
            platform_installs = pd.DataFrame({
                'Platform': ['iOS', 'Android'],
                'Installs': [combined_df['ios_installs'].sum(), combined_df['android_installs'].sum()]
            })
            fig4 = px.pie(platform_installs, values='Installs', names='Platform', title="Installs by Platform")
            st.plotly_chart(fig4, use_container_width=True)

        with col_d:
            fig5 = go.Figure()
            fig5.add_trace(go.Bar(x=combined_df['Date'], y=combined_df['ios_installs'], name='iOS Installs'))
            fig5.add_trace(go.Bar(x=combined_df['Date'], y=combined_df['android_installs'], name='Android Installs'))
            fig5.update_layout(title="Daily Installs by Platform", barmode='stack', height=400)
            st.plotly_chart(fig5, use_container_width=True)

        # 4. CPI Analysis
        st.markdown("---")
        st.header("💵 Cost Efficiency")

        fig6 = go.Figure()
        # replace NaN with None for plotting gaps
        cpi_plot = combined_df['cpi'].where(~combined_df['cpi'].isna(), None)
        fig6.add_trace(go.Scatter(x=combined_df['Date'], y=cpi_plot,
                                  name='CPI', mode='lines+markers', fill='tozeroy'))
        fig6.update_layout(title="Cost Per Install (CPI) Trend", yaxis_title="CPI (₹)", height=400)
        st.plotly_chart(fig6, use_container_width=True)

        # Data Table
        st.markdown("---")
        st.header("📋 Detailed Data")

        display_cols = ['Date', 'Spends', 'total_installs', 'total_kyc', 'total_otp',
                        'cpi', 'install_to_kyc', 'install_to_otp']
        display_df = combined_df[display_cols].copy()
        display_df.columns = ['Date', 'Spend', 'Installs', 'KYC', 'OTP', 'CPI', 'Install→KYC%', 'Install→OTP%']
        display_df['Date'] = display_df['Date'].dt.strftime('%Y-%m-%d')

        st.dataframe(display_df, use_container_width=True, height=400)

        # Key Insights (safe lookups)
        st.markdown("---")
        st.header("💡 Key Insights")

        try:
            if combined_df['cpi'].dropna().size > 0:
                best_cpi_idx = combined_df['cpi'].dropna().idxmin()
                best_cpi_date = combined_df.loc[best_cpi_idx, 'Date'].strftime('%Y-%m-%d')
                best_cpi_val = combined_df.loc[best_cpi_idx, 'cpi']
            else:
                best_cpi_date = "N/A"
                best_cpi_val = np.nan
        except Exception:
            best_cpi_date = "N/A"
            best_cpi_val = np.nan

        try:
            if combined_df['install_to_kyc'].size > 0:
                best_conv_idx = combined_df['install_to_kyc'].idxmax()
                best_conv_date = combined_df.loc[best_conv_idx, 'Date'].strftime('%Y-%m-%d')
                best_conv_val = combined_df.loc[best_conv_idx, 'install_to_kyc']
            else:
                best_conv_date = "N/A"
                best_conv_val = np.nan
        except Exception:
            best_conv_date = "N/A"
            best_conv_val = np.nan

        insight_col1, insight_col2, insight_col3 = st.columns(3)

        with insight_col1:
            st.info(f"**Best CPI Day:** {best_cpi_date}\n\nCPI: {'₹{:.2f}'.format(best_cpi_val) if not pd.isna(best_cpi_val) else 'N/A'}")

        with insight_col2:
            st.success(f"**Best Conversion Day:** {best_conv_date}\n\nInstall→KYC: {best_conv_val:.1f}%" if not pd.isna(best_conv_val) else "N/A")

        with insight_col3:
            avg_conversion = combined_df['install_to_kyc'].replace([np.inf, -np.inf], np.nan).fillna(0).mean()
            st.warning(f"**Average Install→KYC:** {avg_conversion:.1f}%\n\nAverage Install→OTP: {combined_df['install_to_otp'].replace([np.inf, -np.inf], np.nan).fillna(0).mean():.1f}%")

    except Exception as e:
        st.error(f"Error processing files: {str(e)}")
        st.info("Please ensure your CSV files have a Date column and at least one installs/kyc/otp/spend column.")
else:
    st.info("👆 Please upload all three CSV files to begin analysis")

    with st.expander("ℹ️ Expected File Formats"):
        st.markdown("""
        **iOS & Android CSV files should contain (any of these name variants):**
        - Date
        - Installs (or App Store Installs / Play Store Installs / installs)
        - KYC Completed (or KYC)
        - Mobile OTP (or OTP)
        
        **Media Spends CSV file should contain (any of these name variants):**
        - Date
        - Spends / Spend / Amount / Cost / Media Spend
        """)
