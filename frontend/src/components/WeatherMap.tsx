import { memo, useState } from 'react';
import { Marker } from 'react-map-gl/maplibre';
import Map from 'react-map-gl/maplibre';
import 'maplibre-gl/dist/maplibre-gl.css';

// Madison, WI coordinates
const MADISON_COORDS = {
    longitude: -89.37, // Centered better between the two points
    latitude: 43.10,
    zoom: 10.5
};

// Weather stations / Data sources
const DATA_SOURCES = [
    { id: 'KMSN', name: 'Dane County Regional Airport', lat: 43.1398, lon: -89.3375, type: 'NOAA Station' },
    { id: 'W-UW', name: 'Atmospheric & Oceanic Sciences', lat: 43.0728, lon: -89.4072, type: 'Research Station' }
];

export const WeatherMap = memo(function WeatherMap() {
    const [error, setError] = useState<string | null>(null);

    if (error) {
        return (
            <div className="w-full h-full flex items-center justify-center bg-muted/20 rounded">
                <div className="text-center p-4">
                    <p className="text-sm text-muted-foreground">Map unavailable</p>
                    <p className="text-xs text-muted-foreground/60 mt-1">Weather data sources displayed above</p>
                </div>
            </div>
        );
    }

    return (
        <div className="w-full h-full relative overflow-hidden">
            <Map
                initialViewState={MADISON_COORDS}
                style={{ width: '100%', height: '100%' }}
                // Dark matter style similar to pulsera ref but could be standard
                mapStyle="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
                interactive={false} // Static view as requested
                onError={() => setError('Failed to load map')}
            >
                {DATA_SOURCES.map(source => (
                    <Marker
                        key={source.id}
                        longitude={source.lon}
                        latitude={source.lat}
                        anchor="bottom"
                    >
                        <div className="flex flex-col items-center group" aria-label={source.name}>
                            <div className="w-4 h-4 rounded-full bg-primary border-2 border-white shadow-lg group-hover:scale-125 transition-transform" />
                            <div className="mt-1 px-2 py-1 bg-black/80 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
                                {source.name}
                            </div>
                        </div>
                    </Marker>
                ))}
            </Map>
        </div>
    );
})
