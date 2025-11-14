import streamlit as st
import pandas as pd
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

if ios_file and android_file and spend_file:
    try:
        # Read data
        ios_df = pd.read_csv(ios_file)
        android_df = pd.read_csv(android_file)
        spend_df = pd.read_csv(spend_file)
        
        # Standardize column names
        ios_df.columns = ios_df.columns.str.strip()
        android_df.columns = android_df.columns.str.strip()
        spend_df.columns = spend_df.columns.str.strip()
        
        # Convert Date to datetime (MM/DD/YYYY format)
        ios_df['Date'] = pd.to_datetime(ios_df['Date'], format='%m/%d/%Y')
        android_df['Date'] = pd.to_datetime(android_df['Date'], format='%m/%d/%Y')
        spend_df['Date'] = pd.to_datetime(spend_df['Date'], format='%m/%d/%Y')
        
        # Merge data
        ios_df = ios_df.add_prefix('ios_').rename(columns={'ios_Date': 'Date'})
        android_df = android_df.add_prefix('android_').rename(columns={'android_Date': 'Date'})
        
        combined_df = pd.merge(ios_df, android_df, on='Date', how='outer')
        combined_df = pd.merge(combined_df, spend_df, on='Date', how='outer')
        combined_df = combined_df.sort_values('Date').fillna(0)
        
        # Calculate total metrics
        # Handle different possible column names
        install_cols_ios = [col for col in combined_df.columns if 'ios' in col.lower() and 'install' in col.lower()]
        install_cols_android = [col for col in combined_df.columns if 'android' in col.lower() and 'install' in col.lower()]
        
        if install_cols_ios:
            combined_df['ios_installs'] = combined_df[install_cols_ios[0]]
        if install_cols_android:
            combined_df['android_installs'] = combined_df[install_cols_android[0]]
            
        combined_df['total_installs'] = combined_df.get('ios_installs', 0) + combined_df.get('android_installs', 0)
        
        # KYC columns
        kyc_cols_ios = [col for col in combined_df.columns if 'ios' in col.lower() and 'kyc' in col.lower()]
        kyc_cols_android = [col for col in combined_df.columns if 'android' in col.lower() and 'kyc' in col.lower()]
        
        if kyc_cols_ios:
            combined_df['ios_kyc'] = combined_df[kyc_cols_ios[0]]
        if kyc_cols_android:
            combined_df['android_kyc'] = combined_df[kyc_cols_android[0]]
            
        combined_df['total_kyc'] = combined_df.get('ios_kyc', 0) + combined_df.get('android_kyc', 0)
        
        # OTP columns
        otp_cols_ios = [col for col in combined_df.columns if 'ios' in col.lower() and 'otp' in col.lower()]
        otp_cols_android = [col for col in combined_df.columns if 'android' in col.lower() and 'otp' in col.lower()]
        
        if otp_cols_ios:
            combined_df['ios_otp'] = combined_df[otp_cols_ios[0]]
        if otp_cols_android:
            combined_df['android_otp'] = combined_df[otp_cols_android[0]]
            
        combined_df['total_otp'] = combined_df.get('ios_otp', 0) + combined_df.get('android_otp', 0)
        
        # Calculate conversion rates and CPI
        combined_df['install_to_kyc'] = (combined_df['total_kyc'] / combined_df['total_installs'] * 100).fillna(0)
        combined_df['install_to_otp'] = (combined_df['total_otp'] / combined_df['total_installs'] * 100).fillna(0)
        combined_df['kyc_to_otp'] = (combined_df['total_otp'] / combined_df['total_kyc'] * 100).fillna(0).replace([float('inf')], 0)
        combined_df['cpi'] = (combined_df['Spends'] / combined_df['total_installs']).fillna(0).replace([float('inf')], 0)
        
        # Summary Metrics
        st.markdown("---")
        st.header("📈 Key Performance Metrics")
        
        total_spend = combined_df['Spends'].sum()
        total_installs = combined_df['total_installs'].sum()
        total_kyc = combined_df['total_kyc'].sum()
        total_otp = combined_df['total_otp'].sum()
        avg_cpi = total_spend / total_installs if total_installs > 0 else 0
        
        metric_col1, metric_col2, metric_col3, metric_col4, metric_col5 = st.columns(5)
        
        with metric_col1:
            st.metric("Total Spend", f"₹{total_spend:,.0f}")
        with metric_col2:
            st.metric("Total Installs", f"{total_installs:,.0f}")
        with metric_col3:
            st.metric("Avg CPI", f"₹{avg_cpi:.2f}")
        with metric_col4:
            st.metric("Install → KYC", f"{(total_kyc/total_installs*100):.1f}%")
        with metric_col5:
            st.metric("Install → OTP", f"{(total_otp/total_installs*100):.1f}%")
        
        # Visualizations
        st.markdown("---")
        st.header("📊 Impact Analysis")
        
        # 1. Spend vs Installs
        fig1 = make_subplots(specs=[[{"secondary_y": True}]])
        
        fig1.add_trace(
            go.Bar(x=combined_df['Date'], y=combined_df['Spends'], name="Media Spend", marker_color='lightblue'),
            secondary_y=False,
        )
        
        fig1.add_trace(
            go.Scatter(x=combined_df['Date'], y=combined_df['total_installs'], name="Total Installs", 
                      line=dict(color='red', width=3), mode='lines+markers'),
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
                                     name='Installs', mode='lines+markers', line=dict(width=3)))
            fig2.add_trace(go.Scatter(x=combined_df['Date'], y=combined_df['total_kyc'], 
                                     name='KYC Completed', mode='lines+markers', line=dict(width=3)))
            fig2.add_trace(go.Scatter(x=combined_df['Date'], y=combined_df['total_otp'], 
                                     name='Mobile OTP', mode='lines+markers', line=dict(width=3)))
            fig2.update_layout(title="Funnel Progression Over Time", height=400)
            st.plotly_chart(fig2, use_container_width=True)
        
        with col_b:
            fig3 = go.Figure()
            fig3.add_trace(go.Scatter(x=combined_df['Date'], y=combined_df['install_to_kyc'], 
                                     name='Install → KYC %', mode='lines+markers', line=dict(width=3)))
            fig3.add_trace(go.Scatter(x=combined_df['Date'], y=combined_df['install_to_otp'], 
                                     name='Install → OTP %', mode='lines+markers', line=dict(width=3)))
            fig3.update_layout(title="Conversion Rates Over Time", yaxis_title="Conversion %", height=400)
            st.plotly_chart(fig3, use_container_width=True)
        
        # 3. Platform Comparison
        st.markdown("---")
        st.header("🔄 Platform Comparison")
        
        col_c, col_d = st.columns(2)
        
        with col_c:
            platform_installs = pd.DataFrame({
                'Platform': ['iOS', 'Android'],
                'Installs': [combined_df.get('ios_installs', pd.Series([0])).sum(), 
                           combined_df.get('android_installs', pd.Series([0])).sum()]
            })
            fig4 = px.pie(platform_installs, values='Installs', names='Platform', 
                         title="Installs by Platform")
            st.plotly_chart(fig4, use_container_width=True)
        
        with col_d:
            fig5 = go.Figure()
            fig5.add_trace(go.Bar(x=combined_df['Date'], y=combined_df.get('ios_installs', 0), 
                                 name='iOS Installs'))
            fig5.add_trace(go.Bar(x=combined_df['Date'], y=combined_df.get('android_installs', 0), 
                                 name='Android Installs'))
            fig5.update_layout(title="Daily Installs by Platform", barmode='stack', height=400)
            st.plotly_chart(fig5, use_container_width=True)
        
        # 4. CPI Analysis
        st.markdown("---")
        st.header("💵 Cost Efficiency")
        
        fig6 = go.Figure()
        fig6.add_trace(go.Scatter(x=combined_df['Date'], y=combined_df['cpi'], 
                                 name='CPI', mode='lines+markers', line=dict(color='green', width=3),
                                 fill='tozeroy'))
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
        
        # Key Insights
        st.markdown("---")
        st.header("💡 Key Insights")
        
        best_cpi_day = combined_df.loc[combined_df['cpi'] > 0, 'cpi'].idxmin()
        worst_cpi_day = combined_df['cpi'].idxmax()
        best_conversion_day = combined_df['install_to_kyc'].idxmax()
        
        insight_col1, insight_col2, insight_col3 = st.columns(3)
        
        with insight_col1:
            st.info(f"**Best CPI Day:** {combined_df.loc[best_cpi_day, 'Date'].strftime('%Y-%m-%d')}\n\n"
                   f"CPI: ₹{combined_df.loc[best_cpi_day, 'cpi']:.2f}")
        
        with insight_col2:
            st.success(f"**Best Conversion Day:** {combined_df.loc[best_conversion_day, 'Date'].strftime('%Y-%m-%d')}\n\n"
                      f"Install→KYC: {combined_df.loc[best_conversion_day, 'install_to_kyc']:.1f}%")
        
        with insight_col3:
            avg_conversion = combined_df['install_to_kyc'].mean()
            st.warning(f"**Average Install→KYC:** {avg_conversion:.1f}%\n\n"
                      f"Average Install→OTP: {combined_df['install_to_otp'].mean():.1f}%")
        
    except Exception as e:
        st.error(f"Error processing files: {str(e)}")
        st.info("Please ensure your CSV files have the correct format with Date column and relevant metrics.")
else:
    st.info("👆 Please upload all three CSV files to begin analysis")
    
    with st.expander("ℹ️ Expected File Formats"):
        st.markdown("""
        **iOS & Android CSV files should contain:**
        - Date
        - Installs (or App Store Installs / Play Store Installs)
        - KYC Completed (or KYC)
        - Mobile OTP (or OTP)
        
        **Media Spends CSV file should contain:**
        - Date
        - Spends
        """)
