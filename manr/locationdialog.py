#!/usr/bin/env python3

from typing import Any
from geopy.geocoders import Nominatim

from PySide6.QtCore import QObject, Slot, Signal, QUrl, Qt
from PySide6.QtWidgets import QDialogButtonBox
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel

from .datamodel import DataModel
from .grindr_access.grindr_user import GrindrUser

# Import the compiled QRC resources
import manr.map_rc as map_rc  # Registers qrc:/ paths automatically

class MapBridge(QObject):
    coordinatesChanged = Signal(float, float)

    @Slot(float, float)
    def fromMap(self, lat, lon):
        """Called from JS when user clicks on the map."""
        self.coordinatesChanged.emit(lat, lon)

class LocationDialog(QObject):
    ui: Any

    def __init__(self, model: DataModel, parent=None):
        super().__init__()
        self.ui = QUiLoader().load("locationdialog.ui", parent)
        self.model = model
        self.ignoreSignals = False
        self.locationDB = model.getLocationList()
        self.initWebView()
        self.fillLocationNames()
        self.setupConnections()

    def setupConnections(self):
        self.ui.addLocation.clicked.connect(self.on_addLocation_clicked)
        self.ui.removeLocation.clicked.connect(self.on_removeLocation_clicked)
        self.ui.buttonBox.accepted.connect(self.onAccepted)
        self.ui.buttonBox.rejected.connect(self.ui.reject)
        applyBtn = self.ui.buttonBox.button(QDialogButtonBox.StandardButton.Apply)
        applyBtn.clicked.connect(self.onApply)
        self.bridge.coordinatesChanged.connect(self.on_map_coordinatesChanged)
        self.ui.latitude.valueChanged.connect(self.on_coordinates_changed)
        self.ui.longitude.valueChanged.connect(self.on_coordinates_changed)
        self.ui.searchLocation.clicked.connect(self.search_location)
        self.ui.locationList.currentRowChanged.connect(self.on_locationList_currentRowChanged)

    def initWebView(self):
        # WebEngine map
        self.mapWebView = QWebEngineView()
        self.ui.webViewContainer.layout().addWidget(self.mapWebView)

        # Bridge setup
        self.bridge = MapBridge()
        self.channel = QWebChannel()
        self.channel.registerObject("pybridge", self.bridge)
        self.mapWebView.page().setWebChannel(self.channel)

        # Load the HTML from QRC
        self.mapWebView.setUrl(QUrl("qrc:/map.html"))

        # Initialize GeoPy geocoder (Nominatim)
        # TODO/FIXME: Fix email address!
        self.geolocator = Nominatim(user_agent="MyMapApp/1.0 (info@myapp.com)")  # Replace with your app info

    def getLocation(self):
        name = self.ui.locationName.text().strip()
        lat, lon = self.ui.latitude.value(), self.ui.longitude.value()
        return name, (lat, lon)

    def fillLocationNames(self):
        for name in self.locationDB.keys():
            self.ui.locationList.addItem(name)

    def fillLocationDetails(self):
        self.ignoreSignals = True
        try:
            item = self.ui.locationList.currentItem()
            name = item.text() if item else None
            if not name or name not in self.locationDB:
                self.ui.latitude.setValue(0)
                self.ui.longitude.setValue(0)
                self.ui.resolvedAddress.setText("-")
                return
            loc = self.locationDB[name]
            self.ui.locationName.setText(name)
            self.ui.latitude.setValue(loc[0])
            self.ui.longitude.setValue(loc[1])
            self.update_map_from_coordinates()
        finally:
            self.ignoreSignals = False

    def onAccepted(self):
        self.apply_changes()
        self.ui.accept()

    def onApply(self):
        self.apply_changes()

    def on_addLocation_clicked(self):
        name, loc = self.getLocation()
        self.locationDB[name] = loc
        matches = self.ui.locationList.findItems(name, Qt.MatchFlag.MatchExactly)
        if matches:
            item = matches[0]
            self.ui.locationList.setCurrentItem(item)
        else:
            self.ui.locationList.addItem(name)
            self.ui.locationList.setCurrentRow(self.ui.locationList.count()-1)

    def on_removeLocation_clicked(self):
        item = self.ui.locationList.currentItem()
        if not item:
            return
        name = item.text()
        del self.locationDB[name]
        row = self.ui.locationList.row(item)
        self.ignoreSignals = True
        self.ui.locationList.takeItem(row)
        self.ignoreSignals = False
        # Select the next item, or last if we removed the last
        count = self.ui.locationList.count()
        if count > 0:
            new_row = min(row, count - 1)
            self.ui.locationList.setCurrentRow(new_row)

    def on_locationList_currentRowChanged(self):
        self.fillLocationDetails()
        item = self.ui.locationList.currentItem()
        self.ui.removeLocation.setEnabled(item is not None)

    def on_coordinates_changed(self):
        if not self.ignoreSignals:
            self.update_map_from_coordinates()

    def on_map_coordinatesChanged(self, lat, lon):
        """Update Python lat/lon fields when map is clicked."""
        # Skip reverse geocoding if manual update is in progress
        if not self.ignoreSignals:
            self.ui.latitude.setValue(lat)
            self.ui.longitude.setValue(lon)
            self.reverse_geocode(lat, lon)

    def update_map_from_coordinates(self):
        lat = self.ui.latitude.value()
        lon = self.ui.longitude.value()
        self.update_map_view(lat, lon)
        self.reverse_geocode(lat, lon)

    def search_location(self):
        location_name = self.ui.searchText.text()
        if not location_name:
            return
        try:
            self.ignoreSignals = True
            location = self.geolocator.geocode(location_name, addressdetails=True)
            if location:
                lat, lon = location.latitude, location.longitude
                print("location:", location, location.raw)
                self.ui.latitude.setValue(lat)
                self.ui.longitude.setValue(lon)
                self.update_map_from_coordinates()
        except Exception as e:
            print(f"Error geocoding location: {e}")
        finally:
            self.ignoreSignals = False

    def apply_changes(self):
        self.model.setLocationList(self.locationDB)

    def geocode_location(self, location_name):
        """Geocode location name to lat/lon using GeoPy."""
        print("In geocode_location")

    def reverse_geocode(self, lat, lon):
        """Reverse geocode lat/lon to city name using GeoPy."""
        try:
            location = self.geolocator.reverse((lat, lon), language='de, en', addressdetails=True) # type: ignore
            if location:
                address = location.raw.get('address', {}) # type: ignore
                self.ui.resolvedAddress.setText(str(location))
                city_name = self.extract_city_name(address)
                self.ui.locationName.setText(city_name)
                # Zoom map to city level
                self.zoom_to_city(lat, lon)
        except Exception as e:
            print(f"Error reverse geocoding: {e}")

    def extract_city_name(self, address):
        """Extract city name from address data."""
        print("In extract_city_name:", address)
        city = address.get('city', '')
        if not city:
            city = address.get('town', '')  # Fallback to town
        if not city:
            city = address.get('village', '')  # Fallback to village
        return city if city else "Unknown Location"

    def update_map_view(self, lat, lon):
        js = f"updateFromPython({lat}, {lon});"
        self.mapWebView.page().runJavaScript(js)

    def zoom_to_city(self, lat, lon):
        """Zoom the map to a city-level view."""
        # Zoom level 12-14 is ideal for showing a city
        zoom_level = 12
        js = f"map.setView([{lat}, {lon}], {zoom_level});"
        self.mapWebView.page().runJavaScript(js)


def showLocationDialog(model, parent):
    dlg = LocationDialog(model, parent)
    dlg.ui.exec()
    print("Result:", dlg.getLocation())
    return dlg.getLocation()
