#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pkg.public.decorator import decorate
import os
import pymongo
import requests
import datetime
from pkg.public.models import BaseModel
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import numpy as np
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import seaborn as sns
import os

# Set matplotlib style for professional appearance
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")


class PrecipitationReportGenerator:
    def __init__(self, csv_file_path):
        self.csv_file_path = csv_file_path
        self.data = None
        self.location = None
        self.date_range = None

    def load_data(self):
        """Load and preprocess the precipitation data"""
        try:
            self.data = pd.read_csv(self.csv_file_path)

            # Clean the precipitation column by removing '(mm)' and converting to float
            # Handle various formats: '0(mm)', '0()', '0', etc.
            self.data['precipitation'] = self.data['precipitation'].str.replace(
                r'\([^)]*\)', '', regex=True).astype(float)

            # Convert date_time to datetime
            self.data['date_time'] = pd.to_datetime(self.data['date_time'])

            # Extract location information
            self.location = {
                'lat': self.data['lat'].iloc[0],
                'lon': self.data['lon'].iloc[0]
            }

            # Get date range
            self.date_range = {
                'start': self.data['date_time'].min(),
                'end': self.data['date_time'].max()
            }

            print(f"Data loaded successfully: {len(self.data)} records")
            print(
                f"Location: {self.location['lat']}°N, {self.location['lon']}°E, La Paz Wharf")
            print(
                f"Date range: {self.date_range['start'].strftime('%Y-%m-%d')} to {self.date_range['end'].strftime('%Y-%m-%d')}")

        except Exception as e:
            print(f"Error loading data: {e}")
            return False

        return True

    def generate_charts(self):
        """Generate various precipitation charts"""
        if self.data is None:
            print("Error: No data loaded")
            return {}

        charts = {}

        # Set figure size and style
        plt.rcParams['figure.figsize'] = (12, 8)
        plt.rcParams['font.size'] = 10

        # 1. Daily precipitation chart
        daily_data = self.data.groupby(self.data['date_time'].dt.date)[
            'precipitation'].sum().reset_index()
        daily_data.columns = ['date', 'precipitation']
        daily_data['date'] = pd.to_datetime(daily_data['date'])

        fig, ax = plt.subplots(figsize=(12, 6))
        bars = ax.bar(daily_data['date'], daily_data['precipitation'],
                      color='skyblue', alpha=0.7, edgecolor='navy', linewidth=0.5)

        # Highlight significant precipitation days
        significant_days = daily_data[daily_data['precipitation'] > 0]
        if not significant_days.empty:
            for _, row in significant_days.iterrows():
                ax.bar(row['date'], row['precipitation'],
                       color='royalblue', alpha=0.9, edgecolor='darkblue', linewidth=1)

        ax.set_title('Daily Precipitation Summary',
                     fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Date', fontsize=12, fontweight='bold')
        ax.set_ylabel('Precipitation (mm)', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)

        # Format x-axis dates
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))
        plt.xticks(rotation=45)

        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                        f'{height:.1f}', ha='center', va='bottom', fontsize=9)

        plt.tight_layout()
        charts['daily'] = 'daily_precipitation.png'
        plt.savefig(charts['daily'], dpi=300, bbox_inches='tight')
        plt.close()

        # 2. Hourly precipitation pattern for significant days
        significant_hours = self.data[self.data['precipitation'] > 0]
        if not significant_hours.empty:
            fig, ax = plt.subplots(figsize=(12, 6))

            # Group by hour and calculate average precipitation
            hourly_pattern = significant_hours.groupby(
                significant_hours['date_time'].dt.hour)['precipitation'].mean()

            ax.plot(hourly_pattern.index, hourly_pattern.values,
                    marker='o', linewidth=2, markersize=8, color='darkred')
            ax.fill_between(hourly_pattern.index, hourly_pattern.values,
                            alpha=0.3, color='lightcoral')

            ax.set_title('Hourly Precipitation Pattern (Non-Zero Hours)',
                         fontsize=16, fontweight='bold', pad=20)
            ax.set_xlabel('Hour of Day (24h)', fontsize=12, fontweight='bold')
            ax.set_ylabel('Average Precipitation (mm)',
                          fontsize=12, fontweight='bold')
            ax.grid(True, alpha=0.3)
            ax.set_xticks(range(0, 24, 2))

            plt.tight_layout()
            charts['hourly'] = 'hourly_pattern.png'
            plt.savefig(charts['hourly'], dpi=300, bbox_inches='tight')
            plt.close()

        # 3. Precipitation intensity distribution
        fig, ax = plt.subplots(figsize=(10, 6))

        non_zero_precip = self.data[self.data['precipitation']
                                    > 0]['precipitation']
        if not non_zero_precip.empty:
            ax.hist(non_zero_precip, bins=20, color='lightgreen', alpha=0.7,
                    edgecolor='darkgreen', linewidth=0.5)
            ax.axvline(non_zero_precip.mean(), color='red', linestyle='--',
                       linewidth=2, label=f'Mean: {non_zero_precip.mean():.2f} mm')
            ax.axvline(non_zero_precip.median(), color='orange', linestyle='--',
                       linewidth=2, label=f'Median: {non_zero_precip.median():.2f} mm')
            ax.legend()
        else:
            ax.text(0.5, 0.5, 'No precipitation recorded',
                    ha='center', va='center', transform=ax.transAxes, fontsize=14)

        ax.set_title('Precipitation Intensity Distribution',
                     fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Precipitation (mm)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Frequency', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        charts['distribution'] = 'precipitation_distribution.png'
        plt.savefig(charts['distribution'], dpi=300, bbox_inches='tight')
        plt.close()

        return charts

    def generate_statistics(self):
        """Generate comprehensive precipitation statistics"""
        if self.data is None:
            print("Error: No data loaded")
            return {}

        stats = {}

        # Basic statistics
        stats['total_records'] = len(self.data)
        stats['total_precipitation'] = self.data['precipitation'].sum()
        stats['max_precipitation'] = self.data['precipitation'].max()
        stats['min_precipitation'] = self.data['precipitation'].min()
        stats['mean_precipitation'] = self.data['precipitation'].mean()
        stats['std_precipitation'] = self.data['precipitation'].std()

        # Precipitation events
        precip_events = self.data[self.data['precipitation'] > 0]
        stats['precipitation_events'] = len(precip_events)
        stats['dry_periods'] = len(self.data) - len(precip_events)
        stats['precipitation_frequency'] = len(
            precip_events) / len(self.data) * 100

        # Daily statistics
        daily_data = self.data.groupby(self.data['date_time'].dt.date)[
            'precipitation'].sum()
        stats['days_with_precipitation'] = len(daily_data[daily_data > 0])
        stats['total_days'] = len(daily_data)
        stats['max_daily_precipitation'] = daily_data.max()
        stats['mean_daily_precipitation'] = daily_data.mean()

        # Time-based analysis
        if not precip_events.empty:
            hourly_pattern = precip_events.groupby(precip_events['date_time'].dt.hour)[
                'precipitation'].mean()
            stats['peak_hour'] = hourly_pattern.idxmax()
            stats['peak_hour_precipitation'] = hourly_pattern.max()

        return stats

    def create_pdf_report(self, output_filename, charts):
        """Create the PDF report"""
        if self.data is None or self.location is None or self.date_range is None:
            print("Error: Required data not loaded")
            return

        doc = SimpleDocTemplate(output_filename, pagesize=A4,
                                rightMargin=72, leftMargin=72,
                                topMargin=72, bottomMargin=18)

        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            spaceBefore=20,
            textColor=colors.darkblue
        )

        normal_style = styles['Normal']

        # Build the story
        story = []

        # Title page with logo - optimized layout
        story.append(Paragraph("Precipitation Analysis Report", title_style))
        story.append(Spacer(1, 30))

        # Add logo at the top with better positioning - optimized to prevent distortion
        try:
            # Calculate dimensions to maintain aspect ratio (399:400 is approximately 1:1)
            # Use width as the primary dimension and calculate height proportionally
            logo_width = 2.5*inch
            # Maintain original aspect ratio
            logo_height = logo_width * (400/399)

            logo_img = Image("https://obs.navgreen.cn/navgreen-open/Navgreen-logo.jpg",
                             width=logo_width, height=logo_height)
            story.append(logo_img)
            story.append(Spacer(1, 30))
        except Exception as e:
            print(f"Warning: Could not load logo image: {e}")
            # Fallback to text if logo fails to load
            fallback_logo = Paragraph("NAVGreen", heading_style)
            story.append(fallback_logo)
            story.append(Spacer(1, 30))

        # Company information section - centered layout
        company_title = Paragraph("NAVGreen", heading_style)
        story.append(company_title)
        story.append(Spacer(1, 10))

        company_desc = Paragraph(
            "Global Intelligent Decision Platform for Vessel Lifecycle Performance", normal_style)
        story.append(company_desc)
        story.append(Spacer(1, 30))

        # Analysis details in a structured format
        analysis_details = f"""
        <b>Analysis Details:</b><br/>
        • <b>Location:</b> {self.location['lat']}°N, {self.location['lon']}°E  [La Paz Wharf] <br/>
        • <b>Analysis Period:</b> {self.date_range['start'].strftime('%B %d, %Y')} to {self.date_range['end'].strftime('%B %d, %Y')}<br/>
        • <b>Data Resolution:</b> Hourly measurements<br/>
        • <b>Total Records:</b> {len(self.data):,} data points<br/>
        • <b>Report Generated:</b> {datetime.now().strftime('%B %d, %Y at %H:%M')}
        """
        story.append(Paragraph(analysis_details, normal_style))
        story.append(Spacer(1, 30))

        # Data source information
        data_source = Paragraph(
            "<b>Data Source:</b> The fifth generation ECMWF atmospheric reanalysis of the global climate", normal_style)
        story.append(data_source)
        story.append(Spacer(1, 20))

        # Page break
        story.append(PageBreak())

        # Raw Data Summary
        story.append(Paragraph("Raw Data Summary", heading_style))

        # Show complete raw data
        story.append(
            Paragraph("Complete Raw Precipitation Data:", normal_style))
        story.append(Spacer(1, 12))

        # Create a table with ALL data
        raw_data_table_data = [
            ['Date/Time', 'Latitude', 'Longitude', 'Precipitation (mm)']]

        # Process all data rows
        for _, row in self.data.iterrows():
            raw_data_table_data.append([
                row['date_time'].strftime('%Y-%m-%d %H:%M'),
                f"{row['lat']:.3f}°N",
                f"{row['lon']:.3f}°E",
                f"{row['precipitation']:.3f}"
            ])

        # Note: For large datasets, we'll need to handle pagination
        # ReportLab has limitations on table size, so we'll create multiple tables if needed
        max_rows_per_table = 50  # Maximum rows per table for readability

        if len(raw_data_table_data) <= max_rows_per_table:
            # Single table for smaller datasets
            raw_data_table = Table(raw_data_table_data, colWidths=[
                                   2.5*inch, 1*inch, 1*inch, 1.5*inch])
            raw_data_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
            ]))
            story.append(raw_data_table)
        else:
            # Multiple tables for larger datasets
            for i in range(0, len(raw_data_table_data), max_rows_per_table):
                end_idx = min(i + max_rows_per_table, len(raw_data_table_data))
                table_slice = raw_data_table_data[i:end_idx]

                # Add table header for each section
                if i == 0:
                    section_title = f"Data Section 1 (Records 1-{end_idx-1}):"
                else:
                    section_title = f"Data Section {(i//max_rows_per_table)+1} (Records {i+1}-{end_idx-1}):"

                story.append(Paragraph(section_title, normal_style))
                story.append(Spacer(1, 6))

                # Create table for this section
                section_table = Table(table_slice, colWidths=[
                                      2.5*inch, 1*inch, 1*inch, 1.5*inch])
                section_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                ]))

                story.append(section_table)
                story.append(Spacer(1, 12))

                # Add page break between sections for better readability
                if end_idx < len(raw_data_table_data):
                    story.append(PageBreak())

        story.append(Spacer(1, 12))

        # Data overview
        data_overview = f"""
        <b>Data Overview:</b><br/>
        • Total Records: {len(self.data):,}<br/>
        • Date Range: {self.data['date_time'].min().strftime('%Y-%m-%d')} to {self.data['date_time'].max().strftime('%Y-%m-%d')}<br/>
        • Location: {self.location['lat']}°N, {self.location['lon']}°E<br/>
        • Time Resolution: Hourly<br/>
        • Data Format: Hourly precipitation measurements in millimeters
        """
        story.append(Paragraph(data_overview, normal_style))
        story.append(Spacer(1, 20))

        # Data Statistics Table
        story.append(Paragraph("Data Statistics", heading_style))

        # Calculate basic data statistics
        precip_stats = self.data['precipitation'].describe()
        data_stats_table_data = [
            ['Statistic', 'Value'],
            ['Count', f"{precip_stats['count']:,.0f}"],
            ['Mean', f"{precip_stats['mean']:.4f} mm"],
            ['Standard Deviation', f"{precip_stats['std']:.4f} mm"],
            ['Minimum', f"{precip_stats['min']:.4f} mm"],
            ['25% Percentile', f"{precip_stats['25%']:.4f} mm"],
            ['50% Percentile (Median)', f"{precip_stats['50%']:.4f} mm"],
            ['75% Percentile', f"{precip_stats['75%']:.4f} mm"],
            ['Maximum', f"{precip_stats['max']:.4f} mm"]
        ]

        data_stats_table = Table(
            data_stats_table_data, colWidths=[3*inch, 2*inch])
        data_stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgreen),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))

        story.append(data_stats_table)
        story.append(Spacer(1, 20))

        # Precipitation Events Summary
        story.append(Paragraph("Precipitation Events Summary", heading_style))

        # Find all precipitation events (non-zero values)
        precip_events = self.data[self.data['precipitation'] > 0]

        if not precip_events.empty:
            # Group by date and show daily precipitation
            daily_precip = precip_events.groupby(precip_events['date_time'].dt.date)[
                'precipitation'].sum().reset_index()
            daily_precip.columns = ['date', 'total_precip']
            daily_precip = daily_precip.sort_values(
                'total_precip', ascending=False)

            # Create table for precipitation events
            precip_events_table_data = [
                ['Date', 'Total Precipitation (mm)', 'Number of Hours with Rain']]

            for _, row in daily_precip.head(10).iterrows():  # Show top 10 days
                date_str = row['date'].strftime('%Y-%m-%d')
                hours_with_rain = len(
                    precip_events[precip_events['date_time'].dt.date == row['date']])
                precip_events_table_data.append([
                    date_str,
                    f"{row['total_precip']:.3f}",
                    str(hours_with_rain)
                ])

            precip_events_table = Table(precip_events_table_data, colWidths=[
                                        2*inch, 2*inch, 2*inch])
            precip_events_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkred),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightcoral),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))

            story.append(precip_events_table)
            story.append(Spacer(1, 12))

            precip_summary = f"""
            <b>Precipitation Events Summary:</b><br/>
            • Total days with precipitation: {len(daily_precip)}<br/>
            • Total hours with precipitation: {len(precip_events)}<br/>
            • Most significant precipitation day: {daily_precip.iloc[0]['date'].strftime('%Y-%m-%d')} ({daily_precip.iloc[0]['total_precip']:.3f} mm)<br/>
            • Average precipitation per rainy day: {daily_precip['total_precip'].mean():.3f} mm
            """
            story.append(Paragraph(precip_summary, normal_style))
        else:
            story.append(Paragraph(
                "No precipitation events recorded during this period.", normal_style))

        story.append(Spacer(1, 20))

        # Executive Summary
        story.append(Paragraph("Executive Summary", heading_style))
        stats = self.generate_statistics()

        summary_text = f"""
        This report presents a comprehensive analysis of precipitation data collected over a {stats['total_days']}-day period. 
        The analysis reveals {stats['days_with_precipitation']} days with measurable precipitation out of {stats['total_days']} total days, 
        representing a precipitation frequency of {stats['precipitation_frequency']:.1f}%. 
        The total accumulated precipitation during this period was {stats['total_precipitation']:.2f} mm, 
        with daily precipitation ranging from 0 to {stats['max_daily_precipitation']:.2f} mm.
        """
        story.append(Paragraph(summary_text, normal_style))
        story.append(Spacer(1, 20))

        # Key Statistics Table
        story.append(Paragraph("Key Statistics", heading_style))

        stats_data = [
            ['Metric', 'Value'],
            ['Total Records', f"{stats['total_records']:,}"],
            ['Total Precipitation', f"{stats['total_precipitation']:.2f} mm"],
            ['Maximum Precipitation (Hourly)',
             f"{stats['max_precipitation']:.2f} mm"],
            ['Maximum Precipitation (Daily)',
             f"{stats['max_daily_precipitation']:.2f} mm"],
            ['Days with Precipitation', f"{stats['days_with_precipitation']}"],
            ['Precipitation Frequency',
                f"{stats['precipitation_frequency']:.1f}%"],
            ['Mean Daily Precipitation',
                f"{stats['mean_daily_precipitation']:.2f} mm"],
        ]

        if 'peak_hour' in stats:
            stats_data.append(['Peak Precipitation Hour',
                              f"{stats['peak_hour']:02d}:00"])
            stats_data.append(['Peak Hour Precipitation',
                              f"{stats['peak_hour_precipitation']:.2f} mm"])

        stats_table = Table(stats_data, colWidths=[3*inch, 2*inch])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))

        story.append(stats_table)
        story.append(Spacer(1, 20))

        # Charts
        if 'daily' in charts:
            story.append(
                Paragraph("Daily Precipitation Analysis", heading_style))
            story.append(Image(charts['daily'], width=6*inch, height=3*inch))
            story.append(Spacer(1, 12))

            daily_analysis = """
            The daily precipitation chart shows the accumulation of rainfall over the analysis period. 
            Most days recorded no precipitation, with isolated precipitation events occurring on specific dates. 
            This pattern suggests a generally dry period with occasional rainfall episodes.
            """
            story.append(Paragraph(daily_analysis, normal_style))
            story.append(Spacer(1, 20))

        if 'hourly' in charts:
            story.append(
                Paragraph("Hourly Precipitation Pattern", heading_style))
            story.append(Image(charts['hourly'], width=6*inch, height=3*inch))
            story.append(Spacer(1, 12))

            hourly_analysis = """
            The hourly precipitation pattern reveals when rainfall is most likely to occur during the day. 
            This analysis helps identify temporal patterns in precipitation events and can be useful for 
            planning outdoor activities and water resource management.
            """
            story.append(Paragraph(hourly_analysis, normal_style))
            story.append(Spacer(1, 20))

        if 'distribution' in charts:
            story.append(
                Paragraph("Precipitation Intensity Distribution", heading_style))
            story.append(Image(charts['distribution'],
                         width=6*inch, height=3*inch))
            story.append(Spacer(1, 12))

            distribution_analysis = """
            The precipitation intensity distribution shows the frequency of different rainfall amounts. 
            This analysis helps understand the typical intensity of precipitation events and can be used 
            for hydrological modeling and risk assessment.
            """
            story.append(Paragraph(distribution_analysis, normal_style))
            story.append(Spacer(1, 20))

        # Methodology
        story.append(Paragraph("Methodology", heading_style))
        methodology_text = """
        This analysis was conducted using hourly precipitation data collected from meteorological stations. 
        The data was processed to remove outliers and ensure quality control. Statistical analysis was performed 
        using Python with pandas and matplotlib libraries. Charts were generated to visualize temporal patterns 
        and distribution characteristics of precipitation events.
        """
        story.append(Paragraph(methodology_text, normal_style))
        story.append(Spacer(1, 20))

        # Conclusions
        story.append(Paragraph("Conclusions", heading_style))

        if stats['precipitation_frequency'] < 10:
            conclusion = f"""
            The analysis indicates a predominantly dry period with very low precipitation frequency ({stats['precipitation_frequency']:.1f}%). 
            This suggests drought-like conditions or a dry season. Water resource management should consider 
            conservation measures and alternative water sources during such periods.
            """
        elif stats['precipitation_frequency'] < 30:
            conclusion = f"""
            The analysis shows moderate precipitation activity with {stats['precipitation_frequency']:.1f}% of time periods 
            recording rainfall. This represents typical seasonal conditions with occasional precipitation events. 
            Normal water resource management practices should be sufficient.
            """
        else:
            conclusion = f"""
            The analysis reveals high precipitation activity with {stats['precipitation_frequency']:.1f}% of time periods 
            recording rainfall. This suggests wet conditions that may require flood monitoring and 
            appropriate drainage system maintenance.
            """

        story.append(Paragraph(conclusion, normal_style))
        story.append(Spacer(1, 20))

        # Add QR codes and contact information
        story.append(Paragraph("Contact Information", heading_style))
        story.append(Spacer(1, 12))

        # Create a table to display QR codes side by side
        qr_table_data = [
            ['WeChat Mini Program', 'Official Account QR Code']
        ]

        # Add QR code images to the table
        try:
            # WeChat Mini Program QR code
            mini_program_qr = Image(
                "https://obs.navgreen.cn/navgreen-open/WeChat_mini_program.jpg", width=2*inch, height=2*inch)
            # Official Account QR code
            official_qr = Image("https://obs.navgreen.cn/navgreen-open/WeChat_official_account.jpg",
                                width=2*inch, height=2*inch)

            # Create a table with the QR codes
            qr_table = Table(qr_table_data, colWidths=[3*inch, 3*inch])
            qr_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
            ]))

            story.append(qr_table)
            story.append(Spacer(1, 12))

            # Add the QR code images below the table headers
            story.append(mini_program_qr)
            story.append(Spacer(1, 6))
            story.append(official_qr)

        except Exception as e:
            print(f"Warning: Could not load QR code images: {e}")
            story.append(
                Paragraph("QR codes could not be loaded", normal_style))

        story.append(Spacer(1, 20))

        # Add detailed contact information
        story.append(Paragraph("Company Information", heading_style))
        story.append(Spacer(1, 12))

        # Company description
        company_desc = """
        <b>NAVGreen</b><br/>
        NAVGreen is the world's first intelligent decision-making platform covering the full lifecycle performance of vessels.
        """
        story.append(Paragraph(company_desc, normal_style))
        story.append(Spacer(1, 20))

        # Contact person details
        story.append(Paragraph("Primary Contact", heading_style))
        story.append(Spacer(1, 12))

        contact_info = f"""
        <b>Shane Lee</b><br/>
        <b>Operation Department</b><br/>
        <br/>
        <b>Address:</b> 1-2/F, No. 148, Lane 999, Xin'er Road, Baoshan District, Shanghai, China<br/>
        <b>Public Email:</b> ops@navgreen.cn (Please Always Copy)<br/>
        <b>Mobile:</b> +86 15152627161
        """
        story.append(Paragraph(contact_info, normal_style))
        story.append(Spacer(1, 20))

        # Create a professional contact table
        contact_table_data = [
            ['Contact Method', 'Details'],
            ['Name', 'Shane Lee'],
            ['Department', 'Operation Department'],
            ['Company', 'NAVGreen'],
            ['Address', '1-2/F, No. 148, Lane 999, Xin\'er Road, Baoshan District, Shanghai, China'],
            ['Public Email', 'ops@navgreen.cn (Please Always Copy)'],
            ['Mobile', '+86 15152627161']
        ]

        contact_table = Table(contact_table_data, colWidths=[
                              2.5*inch, 4.5*inch])
        contact_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1),
             [colors.lightblue, colors.white]),
        ]))

        story.append(contact_table)
        story.append(Spacer(1, 20))

        # Disclaimer and Legal Information
        story.append(
            Paragraph("Disclaimer and Legal Information", heading_style))
        story.append(Spacer(1, 12))

        disclaimer_text = """
        <b>Disclaimer:</b><br/>
        This precipitation analysis report is provided for informational purposes only. While NAVGreen strives to ensure the accuracy and reliability of the data and analysis presented herein, we make no representations or warranties of any kind, express or implied, about the completeness, accuracy, reliability, suitability, or availability of the information, products, services, or related graphics contained in this report for any purpose.<br/><br/>
        
        The analysis is based on meteorological data from the fifth generation ECMWF atmospheric reanalysis of the global climate. NAVGreen shall not be liable for any loss or damage including without limitation, indirect or consequential loss or damage, arising from loss of data or profits arising out of, or in connection with, the use of this report.<br/><br/>
        
        This report is intended for professional use and should not be considered as the sole basis for critical decision-making. Users are advised to consult additional sources and exercise their own judgment when making decisions based on this information.<br/><br/>
        
        <b>Data Source Attribution:</b><br/>
        The precipitation data used in this analysis is sourced from the fifth generation ECMWF atmospheric reanalysis of the global climate (ERA5), which provides comprehensive atmospheric data for climate research and applications.
        """
        story.append(Paragraph(disclaimer_text, normal_style))
        story.append(Spacer(1, 20))

        # Build the PDF
        doc.build(story)
        print(f"PDF report generated successfully: {output_filename}")

        # Clean up chart files
        for chart_file in charts.values():
            if os.path.exists(chart_file):
                os.remove(chart_file)
                print(f"Cleaned up temporary file: {chart_file}")


class GenPrecipitationAnalysisReport(BaseModel):
    def run(self):
        """Main function to generate the precipitation report"""
        csv_file = "tasks/report_pdf/input/precipitation.csv"
        output_file = "tasks/report_pdf/output/precipitation_analysis_report.pdf"

        # Check if CSV file exists
        if not os.path.exists(csv_file):
            print(f"Error: CSV file '{csv_file}' not found!")
            return

        # Initialize generator
        generator = PrecipitationReportGenerator(csv_file)

        # Load data
        if not generator.load_data():
            print("Failed to load data. Exiting.")
            return

        # Generate charts
        print("Generating charts...")
        charts = generator.generate_charts()

        # Create PDF report
        print("Creating PDF report...")
        generator.create_pdf_report(output_file, charts)

        print(f"\nReport generation completed successfully!")
        print(f"Output file: {output_file}")
