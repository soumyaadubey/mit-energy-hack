// Industrial Emissions Visualization Tool - Main JavaScript

// Global state
let map;
let mapboxToken = '';
let currentFacilities = [];
let simulationResult = null;
let trajectoryChart = null;

// Initialize
async function init() {
    try {
        const response = await fetch('/api/config');
        const config = await response.json();
        mapboxToken = config.mapbox_token;

        // Initialize map
        mapboxgl.accessToken = mapboxToken;
        map = new mapboxgl.Map({
            container: 'map',
            style: 'mapbox://styles/mapbox/light-v11',
            center: config.default_center || [-95.7129, 37.0902],
            zoom: config.default_zoom || 4
        });

        map.on('load', () => {
            console.log('Map loaded');
            // Load sample data on startup
            loadSampleData();
        });

        // Set up event listeners
        setupEventListeners();

    } catch (error) {
        console.error('Error initializing:', error);
    }
}

// Setup all event listeners
function setupEventListeners() {
    // Tab switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });

    // Range sliders
    document.getElementById('min-emissions').addEventListener('input', (e) => {
        const value = parseInt(e.target.value);
        document.getElementById('min-emissions-value').textContent = (value / 1000000).toFixed(1) + 'M';
    });

    document.getElementById('tax-rate').addEventListener('input', (e) => {
        document.getElementById('tax-rate-value').textContent = e.target.value;
    });

    document.getElementById('reduction-target').addEventListener('input', (e) => {
        document.getElementById('reduction-target-value').textContent = e.target.value;
    });

    // Load facilities button
    document.getElementById('load-facilities-btn').addEventListener('click', loadFacilities);

    // Simulate policy button
    document.getElementById('simulate-policy-btn').addEventListener('click', simulatePolicy);

    // Export button
    document.getElementById('export-btn').addEventListener('click', exportData);

    // Layer toggles
    document.getElementById('layer-facilities').addEventListener('change', (e) => {
        toggleLayer('facilities', e.target.checked);
    });

    document.getElementById('layer-labels').addEventListener('change', (e) => {
        toggleLayer('labels', e.target.checked);
    });
}

// Switch tabs
function switchTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active', 'border-primary', 'text-primary');
        btn.classList.add('border-transparent', 'text-muted-foreground');
    });
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active', 'border-primary', 'text-primary');
    document.querySelector(`[data-tab="${tabName}"]`).classList.remove('border-transparent', 'text-muted-foreground');

    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.add('hidden');
    });
    document.getElementById(`tab-${tabName}`).classList.remove('hidden');
}

// Load sample data for demo
async function loadSampleData() {
    try {
        const response = await fetch('/api/sample-data');
        const geojson = await response.json();
        
        currentFacilities = geojson.features;
        displayFacilitiesOnMap(geojson);
        
        document.getElementById('facility-count').textContent = `${geojson.features.length} facilities loaded (sample data)`;
        document.getElementById('facility-count').classList.remove('hidden');
    } catch (error) {
        console.error('Error loading sample data:', error);
    }
}

// Load facilities based on filters
async function loadFacilities() {
    const industries = Array.from(document.querySelectorAll('.industry-filter:checked')).map(cb => cb.value);
    const state = document.getElementById('state-filter').value;
    const year = document.getElementById('year-filter').value;
    const minEmissions = parseInt(document.getElementById('min-emissions').value);

    if (industries.length === 0) {
        alert('Please select at least one industry type');
        return;
    }

    document.getElementById('map-loading').classList.remove('hidden');
    document.getElementById('facility-count').textContent = 'Loading...';
    document.getElementById('facility-count').classList.remove('hidden');

    try {
        // Fetch for each selected industry
        const allFacilities = [];
        
        for (const industry of industries) {
            const params = new URLSearchParams({
                industry_type: industry,
                year: year,
                limit: 1000
            });
            
            if (state) params.append('state', state);
            if (minEmissions > 0) params.append('min_emissions', minEmissions);

            const response = await fetch(`/api/facilities/geojson?${params}`);
            const data = await response.json();
            
            if (data.features) {
                allFacilities.push(...data.features);
            }
        }

        const geojson = {
            type: 'FeatureCollection',
            features: allFacilities
        };

        currentFacilities = allFacilities;
        displayFacilitiesOnMap(geojson);
        
        document.getElementById('facility-count').textContent = `${allFacilities.length} facilities loaded`;

    } catch (error) {
        console.error('Error loading facilities:', error);
        document.getElementById('facility-count').textContent = 'Error loading facilities';
    } finally {
        document.getElementById('map-loading').classList.add('hidden');
    }
}

// Display facilities on map
function displayFacilitiesOnMap(geojson) {
    // Remove existing sources/layers
    if (map.getSource('facilities')) {
        if (map.getLayer('facility-circles')) map.removeLayer('facility-circles');
        if (map.getLayer('facility-labels')) map.removeLayer('facility-labels');
        if (map.getLayer('clusters')) map.removeLayer('clusters');
        if (map.getLayer('cluster-count')) map.removeLayer('cluster-count');
        map.removeSource('facilities');
    }

    // Add source
    map.addSource('facilities', {
        type: 'geojson',
        data: geojson,
        cluster: true,
        clusterMaxZoom: 8,
        clusterRadius: 50
    });

    // Add cluster layer
    map.addLayer({
        id: 'clusters',
        type: 'circle',
        source: 'facilities',
        filter: ['has', 'point_count'],
        paint: {
            'circle-color': [
                'step',
                ['get', 'point_count'],
                '#22c55e',
                10,
                '#eab308',
                25,
                '#f97316',
                50,
                '#ef4444'
            ],
            'circle-radius': [
                'step',
                ['get', 'point_count'],
                20,
                10,
                30,
                25,
                40
            ],
            'circle-opacity': 0.7,
            'circle-stroke-width': 2,
            'circle-stroke-color': '#ffffff'
        }
    });

    // Add cluster count
    map.addLayer({
        id: 'cluster-count',
        type: 'symbol',
        source: 'facilities',
        filter: ['has', 'point_count'],
        layout: {
            'text-field': '{point_count_abbreviated}',
            'text-font': ['DIN Offc Pro Medium', 'Arial Unicode MS Bold'],
            'text-size': 12
        },
        paint: {
            'text-color': '#ffffff'
        }
    });

    // Add individual facility circles
    map.addLayer({
        id: 'facility-circles',
        type: 'circle',
        source: 'facilities',
        filter: ['!', ['has', 'point_count']],
        paint: {
            'circle-color': [
                'match',
                ['get', 'industry'],
                'steel', '#ef4444',
                'cement', '#9ca3af',
                'chemicals', '#3b82f6',
                '#8b5cf6'
            ],
            'circle-radius': [
                'interpolate',
                ['linear'],
                ['get', 'total_emissions'],
                0, 5,
                500000, 10,
                1000000, 15,
                2000000, 20,
                5000000, 30
            ],
            'circle-opacity': 0.8,
            'circle-stroke-width': 2,
            'circle-stroke-color': '#ffffff'
        }
    });

    // Add labels
    map.addLayer({
        id: 'facility-labels',
        type: 'symbol',
        source: 'facilities',
        filter: ['!', ['has', 'point_count']],
        layout: {
            'text-field': ['get', 'name'],
            'text-size': 10,
            'text-offset': [0, 2],
            'text-anchor': 'top',
            'text-optional': true
        },
        paint: {
            'text-color': '#333',
            'text-halo-color': '#ffffff',
            'text-halo-width': 2
        }
    });

    // Add popup on click
    map.on('click', 'facility-circles', (e) => {
        const props = e.features[0].properties;
        
        new mapboxgl.Popup()
            .setLngLat(e.lngLat)
            .setHTML(`
                <div class="p-2">
                    <h3 class="font-semibold text-sm mb-2">${props.name}</h3>
                    <div class="text-xs space-y-1">
                        <div><strong>Industry:</strong> ${props.industry}</div>
                        <div><strong>Location:</strong> ${props.city}, ${props.state}</div>
                        <div><strong>Total Emissions:</strong> ${parseInt(props.total_emissions).toLocaleString()} MT CO₂e/yr</div>
                        <div><strong>CO₂:</strong> ${parseInt(props.co2).toLocaleString()} MT/yr</div>
                        <div><strong>Year:</strong> ${props.year}</div>
                        ${props.violations > 0 ? `<div class="text-red-600"><strong>Violations:</strong> ${props.violations}</div>` : ''}
                        ${props.parent_company ? `<div><strong>Parent:</strong> ${props.parent_company}</div>` : ''}
                    </div>
                </div>
            `)
            .addTo(map);
    });

    // Cluster click to zoom
    map.on('click', 'clusters', (e) => {
        const features = map.queryRenderedFeatures(e.point, { layers: ['clusters'] });
        const clusterId = features[0].properties.cluster_id;
        map.getSource('facilities').getClusterExpansionZoom(clusterId, (err, zoom) => {
            if (err) return;
            map.easeTo({
                center: features[0].geometry.coordinates,
                zoom: zoom
            });
        });
    });

    // Change cursor on hover
    map.on('mouseenter', 'facility-circles', () => {
        map.getCanvas().style.cursor = 'pointer';
    });
    map.on('mouseleave', 'facility-circles', () => {
        map.getCanvas().style.cursor = '';
    });
    map.on('mouseenter', 'clusters', () => {
        map.getCanvas().style.cursor = 'pointer';
    });
    map.on('mouseleave', 'clusters', () => {
        map.getCanvas().style.cursor = '';
    });

    // Fit map to facilities
    if (geojson.features.length > 0) {
        const bounds = new mapboxgl.LngLatBounds();
        geojson.features.forEach(feature => {
            bounds.extend(feature.geometry.coordinates);
        });
        map.fitBounds(bounds, { padding: 50, maxZoom: 10 });
    }
}

// Simulate policy
async function simulatePolicy() {
    const scenarioName = document.getElementById('scenario-name').value;
    const taxRate = parseFloat(document.getElementById('tax-rate').value);
    const taxType = document.getElementById('tax-type').value;
    const phaseInYears = parseInt(document.getElementById('phase-in-years').value);
    const reductionTarget = parseFloat(document.getElementById('reduction-target').value);
    const targetYear = parseInt(document.getElementById('target-year').value);
    const targetIndustries = Array.from(document.querySelectorAll('.policy-industry:checked')).map(cb => cb.value);

    if (targetIndustries.length === 0) {
        alert('Please select at least one industry to apply the policy to');
        return;
    }

    // Build filtering requirements
    const filteringRequirements = [];
    if (document.getElementById('require-ccs').checked) {
        filteringRequirements.push({
            technology_type: "Carbon Capture",
            capture_efficiency: 90.0,
            capital_cost_per_facility: 150000000,
            annual_operating_cost: 12000000,
            applicable_industries: targetIndustries
        });
    }
    if (document.getElementById('require-scrubbers').checked) {
        filteringRequirements.push({
            technology_type: "Scrubber",
            capture_efficiency: 70.0,
            capital_cost_per_facility: 50000000,
            annual_operating_cost: 2500000,
            applicable_industries: targetIndustries
        });
    }
    if (document.getElementById('require-process-improvement').checked) {
        filteringRequirements.push({
            technology_type: "Process Improvement",
            capture_efficiency: 20.0,
            capital_cost_per_facility: 30000000,
            annual_operating_cost: 900000,
            applicable_industries: targetIndustries
        });
    }

    const scenario = {
        scenario_name: scenarioName,
        description: `Policy simulation for ${targetIndustries.join(', ')}`,
        target_industries: targetIndustries,
        phase_in_period_years: phaseInYears
    };

    if (taxRate > 0) {
        scenario.carbon_tax = {
            tax_rate_per_ton_co2e: taxRate,
            tax_type: taxType,
            phase_in_years: phaseInYears
        };
    }

    if (reductionTarget > 0) {
        scenario.emissions_cap = {
            target_year: targetYear,
            reduction_percentage: reductionTarget,
            baseline_year: 2022
        };
    }

    if (filteringRequirements.length > 0) {
        scenario.filtering_requirements = filteringRequirements;
    }

    document.getElementById('simulation-status').classList.remove('hidden');
    document.getElementById('simulation-status').textContent = 'Simulating policy impact...';
    document.getElementById('simulate-policy-btn').disabled = true;

    try {
        const response = await fetch('/api/policy/simulate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(scenario)
        });

        simulationResult = await response.json();
        displayResults(simulationResult);
        switchTab('results');

    } catch (error) {
        console.error('Error simulating policy:', error);
        alert('Error simulating policy. Please try again.');
    } finally {
        document.getElementById('simulation-status').classList.add('hidden');
        document.getElementById('simulate-policy-btn').disabled = false;
    }
}

// Display simulation results
function displayResults(result) {
    document.getElementById('no-results').classList.add('hidden');
    document.getElementById('results-content').classList.remove('hidden');

    // Key metrics
    const reduction = (result.emissions_reduction_mt_co2e / 1000000).toFixed(2);
    document.getElementById('result-reduction').textContent = `${reduction}M MT`;
    document.getElementById('result-reduction-pct').textContent = `${result.emissions_reduction_percentage.toFixed(1)}% reduction`;
    
    document.getElementById('result-facilities').textContent = result.facilities_affected.toLocaleString();
    
    const revenue = (result.total_carbon_tax_revenue / 1000000000).toFixed(2);
    document.getElementById('result-revenue').textContent = `$${revenue}B`;
    
    const cost = (result.total_compliance_cost / 1000000000).toFixed(2);
    document.getElementById('result-cost').textContent = `$${cost}B`;

    // Industry breakdown
    const breakdownHtml = Object.entries(result.impact_by_industry).map(([industry, data]) => {
        const emissions = (data.total_emissions / 1000000).toFixed(1);
        const cost = (data.tax_cost / 1000000).toFixed(1);
        return `
            <div class="flex justify-between items-center py-1 border-b">
                <span class="font-medium capitalize">${industry}</span>
                <div class="text-right">
                    <div>${data.facilities_count} facilities</div>
                    <div class="text-xs text-muted-foreground">${emissions}M MT CO₂e</div>
                </div>
            </div>
        `;
    }).join('');
    document.getElementById('industry-breakdown').innerHTML = breakdownHtml;

    // Emissions trajectory chart
    displayTrajectoryChart(result.emissions_trajectory);
}

// Display emissions trajectory chart
function displayTrajectoryChart(trajectory) {
    const ctx = document.getElementById('trajectory-chart').getContext('2d');
    
    if (trajectoryChart) {
        trajectoryChart.destroy();
    }

    const years = trajectory.map(t => t.year);
    const emissions = trajectory.map(t => t.emissions_mt_co2e / 1000000);

    trajectoryChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: years,
            datasets: [{
                label: 'Projected Emissions (M MT CO₂e)',
                data: emissions,
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                tension: 0.3,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    title: {
                        display: true,
                        text: 'Million MT CO₂e'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Year'
                    }
                }
            }
        }
    });
}

// Toggle map layers
function toggleLayer(layerType, visible) {
    if (layerType === 'facilities') {
        map.setLayoutProperty('facility-circles', 'visibility', visible ? 'visible' : 'none');
        map.setLayoutProperty('clusters', 'visibility', visible ? 'visible' : 'none');
        map.setLayoutProperty('cluster-count', 'visibility', visible ? 'visible' : 'none');
    } else if (layerType === 'labels') {
        if (map.getLayer('facility-labels')) {
            map.setLayoutProperty('facility-labels', 'visibility', visible ? 'visible' : 'none');
        }
    }
}

// Export data
async function exportData() {
    const industries = Array.from(document.querySelectorAll('.industry-filter:checked')).map(cb => cb.value);
    const state = document.getElementById('state-filter').value;
    const year = document.getElementById('year-filter').value;

    if (industries.length === 0) {
        alert('Please select at least one industry type to export');
        return;
    }

    const industry = industries[0]; // Export first selected industry
    const params = new URLSearchParams({
        industry_type: industry,
        year: year
    });
    
    if (state) params.append('state', state);

    window.location.href = `/api/export/facilities/csv?${params}`;
}

// Initialize on load
document.addEventListener('DOMContentLoaded', init);
