import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5 import QtCore, QtGui, QtWidgets
from gui import Ui_MainWindow  
import pdb, os, sys
from pathlib import Path
from matplotlib.figure import Figure
import requests
import folium
from contextlib import redirect_stdout
import io
import sys
from PyQt5.QtWidgets import QMessageBox, QApplication, QMainWindow, QTextEdit, QPushButton, QVBoxLayout, QWidget, QFileDialog, QLabel
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtGui import *


##reading and cleaning data
class DataHandler:
    def __init__(self):
        pass

    def clean_data(self, file_path):
        try:
            df = pd.read_excel(file_path)
        
            # Cleaning Data
            df = df.drop_duplicates()
            df = df.drop(columns=["Region", "ISO3", "Reference", "Number and type of monitoring stations",
                                  "PM25 temporal coverage (%)", "PM10 temporal coverage (%)", "NO2 temporal coverage (%)"])
            df = df[~df['Year'].isin(range(2000, 2010)) & ~df['Year'].isin(range(2020, 2024))]
        
            return df
        except Exception as e:
            print("Error cleaning data:", e)
            return None

class MainWindow(QtWidgets.QMainWindow):
    
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        ##define variables
        self.setWindowTitle("First Project in Data Analyzing")
        self.data_handler = DataHandler()
        self.dataframe = None
        self.current_plot = None
        self.year_plot = None
        self.country_plot = None

        ##add and connect to widgets in sampletest GUI file
        self.ui.tabWidget.setTabText(0, "Histograms")
        self.ui.tabWidget.setTabText(1, "Compare Countries")
        self.ui.tabWidget.setTabText(2, "Rate Plot")
        self.ui.tabWidget.setTabText(3, "Map")
        self.ui.tabWidget_2.setTabText(0, "Data Processing")
        self.ui.tabWidget_2.setTabText(1, "Image Processing")

        self.ui.Select.clicked.connect(self.select_file)
        self.ui.pbPlot.clicked.connect(self.plot_selected_pollutant)
        self.ui.PlotTab1.clicked.connect(self.plot_mean_pollutants_by_year)
        self.ui.cbYTab1.currentIndexChanged.connect(self.update_year_plot)
        self.ui.pbPlot_3.clicked.connect(self.plot_country_pollutants)
        self.ui.pbPlot_2.clicked.connect(self.plot_selected_countries_pollutants)  # Added this line
        self.ui.ratePlot.clicked.connect(self.plot_rate_pollutants)
        self.ui.mapbtn.clicked.connect(self.create_map_with_air_quality_data)
        self.web_view = QWebEngineView()
        self.ui.maplayout.addWidget(self.web_view)
        self.load_years()
        self.ui.corrbtn.clicked.connect(self.show_correlation_popup)
        
        self.ui.groupBox_5.setTitle("Original Image")
        self.ui.groupBox_3.setTitle("Object Detected Image")


    def select_file(self):
        file_dialog = QtWidgets.QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(self, "Select Excel File", "", "Excel Files (*.xlsx)")

        if file_path:
            self.dataframe = self.data_handler.clean_data(file_path)
            self.ui.DataName.setText(file_path)
            self.load_pollutants()
            self.load_years()
            self.load_countries_tab3()
            self.setup_tab2()

    ##loading pollutants(3columns) in choosePollutant1 combobox in Tab1(Histograms) of Data Processing  
    def load_pollutants(self):
        if self.dataframe is not None:
            pollutants = [col for col in self.dataframe.columns if any(poll in col for poll in ['NO2', 'PM2.5', 'PM10'])]
            self.ui.choosePollutant1.clear()
            self.ui.choosePollutant1.addItems(pollutants)

    ##loading years in cbYTab1 combobox in Tab1(Histograms) of Data Processing
    def load_years(self):
        if self.dataframe is not None:
            years_2010_to_2019 = self.dataframe[self.dataframe['Year'].between(2010, 2019)]['Year'].unique()
            self.ui.cbYTab1.clear()
            self.ui.cbYTab1.addItems([str(year) for year in years_2010_to_2019])
     
    ##loading countries in cbCountTab3 combobox in Tab3(Rate Plot) of Data Processing
    def load_countries_tab3(self):
        if self.dataframe is not None:
            countries = self.dataframe['Country'].unique()
            self.ui.cbCountTab3.clear()
            self.ui.cbCountTab3.addItems(countries)

    ##ploting histograms by 3 following functions
    ##Histograms of all countries during years for every pollutant
    def plot_selected_pollutant(self):
        if self.dataframe is None:
            return

        selected_pollutant = self.ui.choosePollutant1.currentText()
        mean_value = self.dataframe.groupby('Country')[selected_pollutant].mean().nlargest(20)

        if self.current_plot:
            self.ui.verticalLayout_9.removeWidget(self.current_plot)
            self.current_plot.deleteLater()
            self.current_plot = None

        new_plot = plt.figure(figsize=(6, 6))
        ax = new_plot.add_subplot(111)
        ax.bar(mean_value.index, mean_value.values)
        ax.set_title(f'Top 20 Countries for {selected_pollutant}')
        ax.set_xlabel('Countries')
        ax.set_ylabel('Mean Pollutant Level')
        ax.tick_params(axis='x', rotation=90)
        ax.figure.tight_layout()

        canvas = FigureCanvas(new_plot)
        self.ui.verticalLayout_9.addWidget(canvas)
        self.ui.verticalLayout_9.update()
        self.current_plot = canvas

    ##Histogram of countries for chosen pollutant and year
    def plot_mean_pollutants_by_country_year(self, dataframe, pollutant_column, constant_means):
        if self.year_plot:
            self.ui.verticalLayout_7.removeWidget(self.year_plot)
            self.year_plot.deleteLater()
            self.year_plot = None

        mean_value = dataframe.groupby(['Country', 'Year'])[pollutant_column].mean().reset_index()
        top20_country_year = mean_value.groupby('Year').apply(lambda x: x.nlargest(20, pollutant_column)).reset_index(drop=True)

        for year, data in top20_country_year.groupby('Year'):
            plt.figure(figsize=(6, 6))
            plt.bar(data['Country'], data[pollutant_column], label='Top 20 Countries', alpha=0.7)

            for idx, (mean_val, custom_label, line_style) in enumerate(constant_means):
                linestyle = '-' if line_style == 'solid' else '--'
                plt.axhline(y=mean_val, color='red', linestyle=linestyle, label=custom_label)

            plt.title(f'Top 20 Polluted Countries for {pollutant_column} in {year}')
            plt.xlabel('Countries')
            plt.ylabel(pollutant_column)
            plt.legend()
            plt.xticks(rotation=90)
            plt.tight_layout()

            canvas = FigureCanvas(plt.gcf())
            self.ui.verticalLayout_7.addWidget(canvas)
            self.ui.verticalLayout_7.update()
            self.year_plot = canvas

    def plot_mean_pollutants_by_year(self):
        if self.dataframe is None:
            return

        selected_pollutant = self.ui.choosePollutant1.currentText()
        selected_year = int(self.ui.cbYTab1.currentText())

        pollutants_means = {
            'NO2 (μg/m3)': [(40, '2005 AQG(40)', 'solid'), (10, 'Revised in 2021 AQG(10)', 'dashed')],
            'PM2.5 (μg/m3)': [(10, '2005 AQG(10)', 'solid'), (5, 'Revised in 2021 AQG(5)', 'dashed')],
            'PM10 (μg/m3)': [(20, '2005 AQG(20)', 'solid'), (15, 'Revised in 2021 AQG(15)', 'dashed')]
        }

        plot_data = pollutants_means.get(selected_pollutant)

        if plot_data:
            if self.year_plot:
                self.ui.verticalLayout_7.removeWidget(self.year_plot)
                self.year_plot.deleteLater()
                self.year_plot = None

            self.plot_mean_pollutants_by_country_year(
                self.dataframe[self.dataframe['Year'] == selected_year],
                selected_pollutant,
                plot_data
            )

    ##update plot by changing year
    def update_year_plot(self):
        if self.year_plot:
            self.ui.verticalLayout_7.removeWidget(self.year_plot)
            self.year_plot.deleteLater()
            self.year_plot = None
            self.plot_mean_pollutants_by_year()

    ##rate plot for each country in Tab3(Rate Plot) in Data Processing
    def plot_pollutants_for_each_country(self):
        if self.dataframe is None:
            return

        selected_country = self.ui.cbCountTab3.currentText()
        pollutant_columns = ['NO2 (μg/m3)', 'PM2.5 (μg/m3)', 'PM10 (μg/m3)']

        plt.figure(figsize=(6, 6))

        country_data = self.dataframe[self.dataframe['Country'] == selected_country]
        grouped_data = country_data.groupby('Year')[pollutant_columns].mean().reset_index()

        years = grouped_data['Year']

        for pollutant_column in pollutant_columns:
            mean_values = grouped_data[pollutant_column]
            plt.plot(years, mean_values, marker='o', label=pollutant_column)

        plt.xlabel('Years')
        plt.ylabel('Mean Value')
        plt.title(f'Mean Values of Pollutants for {selected_country}')
        plt.legend()
        plt.tight_layout()

        if self.country_plot:
            self.ui.verticalLayout_16.removeWidget(self.country_plot)
            self.country_plot.deleteLater()
            self.country_plot = None

        canvas = FigureCanvas(plt.gcf())
        self.ui.verticalLayout_16.addWidget(canvas)
        self.ui.verticalLayout_16.update()
        self.country_plot = canvas

    def plot_country_pollutants(self):
        self.plot_pollutants_for_each_country()

    ##load countries in the list view in Tab2(Compare countries) in Data Processing
    def load_countries_to_listview(self):
        if self.dataframe is not None:
            countries = self.dataframe['Country'].unique()
            model = QtGui.QStandardItemModel()
            for country in countries:
                item = QtGui.QStandardItem(country)
                item.setCheckable(True)
                model.appendRow(item)
            self.ui.listView.setModel(model)

    ##plot histogram of selected countries in Tab2 of Data Processing using QTgrapg
    def plot_selected_countries_pollutants(self):
        selected_countries = []
        model = self.ui.listView.model()
        for row in range(model.rowCount()):
            item = model.item(row)
            if item.checkState() == QtCore.Qt.Checked:
                selected_countries.append(item.text())
        selected_year = int(self.ui.cbYTab2.currentText())
        selected_pollutant = self.ui.PollutTab2.currentText()
    
        if not selected_countries:  # No countries selected
            return
    
        fig = Figure(figsize=(8, 5))
        ax = fig.add_subplot(111)
    
        # Replace the existing loop with the new logic
        for country in selected_countries:
            country_data = self.dataframe[
                (self.dataframe['Country'] == country) & (self.dataframe['Year'] == selected_year)]
    
            # New logic starts here
            if len(country_data[selected_pollutant].values) > 0:
                try:
                    ax.bar(country, country_data[selected_pollutant].values[0], label=country)
                except IndexError as e:
                    # Handle the IndexError here
                    print(f"IndexError occurred for {country} and {selected_pollutant}: {e}")
                    # You can add other actions or error handling here
            else:
                # Handle the case where the array is empty
                print(f"No data available for {country} and {selected_pollutant}")
            # New logic ends here
    
        ax.set_xlabel('Countries')
        ax.set_ylabel(selected_pollutant)
        ax.set_title(f'{selected_pollutant} for Selected Countries in {selected_year}')
        ax.legend()
        fig.tight_layout()
    
        self.update_plot_in_tab2(fig)
 

    def update_plot_in_tab2(self, plot):
        if self.country_plot:
            self.ui.verticalLayout_14.removeWidget(self.country_plot)
            self.country_plot.deleteLater()
            self.country_plot = None

        canvas = FigureCanvas(plot)
        self.ui.verticalLayout_14.addWidget(canvas)
        self.ui.verticalLayout_14.update()
        self.country_plot = canvas

    def connect_tab2_buttons(self):
        self.ui.pbPlot_2.clicked.connect(self.plot_selected_countries_pollutants)

    def setup_tab2(self):
        self.load_countries_to_listview()
        self.load_years_tab2()
        self.load_pollutants_tab2()
        self.connect_tab2_buttons()

    def load_years_tab2(self):
        if self.dataframe is not None:
            years = self.dataframe['Year'].unique()
            self.ui.cbYTab2.clear()
            self.ui.cbYTab2.addItems([str(year) for year in years])

    def load_pollutants_tab2(self):
        pollutants = ['NO2 (μg/m3)', 'PM2.5 (μg/m3)', 'PM10 (μg/m3)']
        self.ui.PollutTab2.clear()
        self.ui.PollutTab2.addItems(pollutants)

    ##rate plot of for all countries Tab3 in Data Processing
    def plot_rate_pollutants(self):
        if self.dataframe is None:
            return
    
        pollutants = ['NO2 (μg/m3)', 'PM2.5 (μg/m3)', 'PM10 (μg/m3)']
        years = sorted(self.dataframe['Year'].unique())
    
        fig, ax = plt.subplots(figsize=(6, 6))
    
        for pollutant in pollutants:
            mean_values = self.dataframe.groupby('Year')[pollutant].mean().loc[years]
            ax.plot(years, mean_values, label=pollutant)
    
        ax.set_xlabel('Year')
        ax.set_ylabel('Mean Pollutant Level')
        ax.set_title('Mean Pollutant Levels Over the Years')
        ax.legend()
        plt.tight_layout()
    
        self.update_rate_plot(fig)

    def update_rate_plot(self, plot):
        if self.current_plot:
            self.ui.verticalLayout_11.removeWidget(self.current_plot)
            self.current_plot.deleteLater()
            self.current_plot = None
    
        canvas = FigureCanvas(plot)
        self.ui.verticalLayout_11.addWidget(canvas)
        self.ui.verticalLayout_11.update()
        self.current_plot = canvas

    ##correlation coefficient heatmap in a popup window in Data Processing
    def show_correlation_popup(self):
        if self.dataframe is None:
            file_dialog = QtWidgets.QFileDialog()
            file_path,_ = file_dialog.getOpenFileName(self,"Select Excel File","","Excel File (*.xlsx)")
            if file_path:
                self.dataframe = self.data_handler.clean_data(file_path)

        if self.dataframe is not None:
            correlation_matrix = self.dataframe[['NO2 (μg/m3)', 'PM2.5 (μg/m3)', 'PM10 (μg/m3)']].corr()

            sns.set(style="white")
            plt.figure(figsize=(8,6))
            plt.gca().set_aspect('equal')
            sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', fmt=".2f",linewidths=.5)
            plt.title('Correlation Heatmap of Air Pollutants')

            canvas=FigureCanvas(plt.gcf())
            widget = QWidget()
            layout = QVBoxLayout(widget)
            layout.addWidget(canvas)

            popup = QtWidgets.QDialog(self)
            popup.setWindowTitle("Correlation Coefficient")
            popup.setLayout(layout)
            popup.exec_()
            plt.close()

        else:
            QMessageBox.warning(self, "Data Not Loaded", "Load Data", QMessageBox.ok)


    ##showing data on map using API in Tab4(map) in Data Processing 
    def create_map_with_air_quality_data(self):
        def get_air_quality_data(lat, lon, api_key):
            url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid="
            response = requests.get(url)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Failed to fetch air quality data for lat={lat}, lon={lon}. Error: {response.text}")
                return None
        cities = [
            {"name": "Paris", "latitude": 48.8566, "longitude": 2.3522},
            {"name": "Islamabad", "latitude": 33.6844, "longitude": 73.0479},
            {"name": "Tehran", "latitude": 35.6892, "longitude": 51.3890},
            {"name": "Berlin", "latitude": 52.5200, "longitude": 13.4050},
            {"name": "Riyadh", "latitude": 24.7136, "longitude": 46.6753},
            {"name": "Beijing", "latitude": 39.9042, "longitude": 116.4074},
            {"name": "Washington", "latitude": 38.8951, "longitude": -77.0364},
            {"name": "New York", "latitude": 40.7128, "longitude": -74.0060},
            {"name": "Copenhagen", "latitude": 55.6761, "longitude": 12.5683},
            {"name": "Amsterdam", "latitude": 52.3676, "longitude": 4.9041},
            {"name": "Madrid", "latitude": 40.4168, "longitude": -3.7038},
            {"name": "London", "latitude": 51.5074, "longitude": -0.1278},
            {"name": "Brasilia", "latitude": -15.8267, "longitude": -47.9218},
            {"name": "Ottawa", "latitude": 45.4215, "longitude": -75.6972},
            {"name": "Brasilia", "latitude": -15.8267, "longitude": -47.9218},  # Brazil
            {"name": "Ottawa", "latitude": 45.4215, "longitude": -75.6972},  # Canada
            {"name": "Mexico City", "latitude": 19.4326, "longitude": -99.1332},  # Mexico
            {"name": "Buenos Aires", "latitude": -34.6037, "longitude": -58.3816},  # Argentina
            {"name": "Bogota", "latitude": 4.7110, "longitude": -74.0721},  # Colombia
            {"name": "Bern", "latitude": 46.9480, "longitude": 7.4474},  # Switzerland
            {"name": "Vienna", "latitude": 48.2082, "longitude": 16.3738},  # Austria
            {"name": "Canberra", "latitude": -35.2820, "longitude": 149.1286},  # Australia
            {"name": "Stockholm", "latitude": 59.3293, "longitude": 18.0686},  # Sweden
            {"name": "Brussels", "latitude": 50.8503, "longitude": 4.3517},  # Belgium
            {"name": "Kiev", "latitude": 50.4501, "longitude": 30.5234},  # Ukraine
            {"name": "Moscow", "latitude": 55.7558, "longitude": 37.6176},  # Russia
            {"name": "Tokyo", "latitude": 35.6895, "longitude": 139.6917},  # Japan
            {"name": "Bangkok", "latitude": 13.7563, "longitude": 100.5018},  # Thailand
            {"name": "New Delhi", "latitude": 28.6139, "longitude": 77.2090},  # India
            {"name": "Hong Kong", "latitude": 22.3193, "longitude": 114.1694},  # Hong Kong
            {"name": "Seoul", "latitude": 37.5665, "longitude": 126.9780},  # South Korea
            {"name": "Pyongyang", "latitude": 39.0392, "longitude": 125.7625},  # North Korea
            {"name": "Baghdad", "latitude": 33.3152, "longitude": 44.3661},  # Iraq
            {"name": "Damascus", "latitude": 33.5138, "longitude": 36.2765},  # Syria
            {"name": "Kuwait City", "latitude": 29.3759, "longitude": 47.9774},  # Kuwait
            {"name": "Manama", "latitude": 26.2285, "longitude": 50.5860},  # Bahrain
            {"name": "Amman", "latitude": 31.9522, "longitude": 35.2332},  # Jordan
            {"name": "Abu Dhabi", "latitude": 24.4539, "longitude": 54.3773},  # United Arab Emirates
            {"name": "Kabul", "latitude": 34.5553, "longitude": 69.2075},  # Afghanistan
            {"name": "Baku", "latitude": 40.4093, "longitude": 49.8671},  # Azerbaijan
            {"name": "Ankara", "latitude": 39.9334, "longitude": 32.8597},  # Turkey
            {"name": "Abuja", "latitude": 9.0765, "longitude": 7.3986},  # Nigeria
            {"name": "Cairo", "latitude": 30.0444, "longitude": 31.2357},  # Egypt
            {"name": "Rabat", "latitude": 34.0209, "longitude": -6.8415},  # Morocco
            {"name": "Algiers", "latitude": 36.7372, "longitude": 3.0870},  # Algeria
            {"name": "Pretoria", "latitude": -25.7463, "longitude": 28.1876},  # South Africa
            {"name": "Kinshasa", "latitude": -4.4419, "longitude": 15.2663},  # Congo
            {"name": "Helsinki", "latitude": 60.1695, "longitude": 24.9354},  # Finland
            {"name": "Dublin", "latitude": 53.3498, "longitude": -6.2603},  # Ireland
            {"name": "Oslo", "latitude": 59.9139, "longitude": 10.7522},  # Norway
            {"name": "Rome", "latitude": 41.9028, "longitude": 12.4964},  # Italy
            {"name": "Warsaw", "latitude": 52.2297, "longitude": 21.0122},  # Poland
            {"name": "Zagreb", "latitude": 45.8150, "longitude": 15.9819},  # Croatia
            {"name": "Niamey", "latitude": 13.5127, "longitude": 2.1126},  # Niger
            {"name": "Tripoli", "latitude": 32.8872, "longitude": 13.1913},  # Libya
            {"name": "Kampala", "latitude": 0.3476, "longitude": 32.5825},  # Uganda
            {"name": "Bamako", "latitude": 12.6392, "longitude": -8.0029},  # Mali
            {"name": "Khartoum", "latitude": 15.5007, "longitude": 32.5599},  # Sudan
            {"name": "Sucre", "latitude": -19.0196, "longitude": -65.2619},  # Bolivia
            # Add capitals here
            # Format: {"name": "City", "latitude": latitude_value, "longitude": longitude_value}
        ]
    
        m = folium.Map(location=[20, 0], zoom_start=10)
    
    
        for city in cities:
            data = get_air_quality_data(city['latitude'], city['longitude'], "YOUR_OPENWEATHERMAP_API_KEY")
            if data and 'list' in data and len(data['list']) > 0:
                pollutants = data['list'][0]['components']
                popup_text = f"City: {city['name']}<br>PM2.5: {pollutants.get('pm2_5')}<br>PM10: {pollutants.get('pm10')}<br>NO2: {pollutants.get('no2')}"
                folium.Marker([city['latitude'], city['longitude']], popup=folium.Popup(popup_text, max_width=1000)).add_to(m)
            else:
                folium.Marker([city['latitude'], city['longitude']], popup=f"No data available for {city['name']}").add_to(m)
        
        data = io.BytesIO()
        m.save(data, close_file=False)
        self.web_view.setHtml(data.getvalue().decode())
   

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
