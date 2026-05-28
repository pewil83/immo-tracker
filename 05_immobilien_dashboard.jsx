import React, { useState, useEffect } from 'react';
import { ChevronDown, Search, TrendingUp, Home, DollarSign, AlertCircle, Filter } from 'lucide-react';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

export default function ImmobilienDashboard() {
  const [stats, setStats] = useState({
    total: 0,
    neu_heute: 0,
    durchschnittspreis: 0,
    duplikate: 0
  });
  
  const [immobilien, setImmobilien] = useState([]);
  const [duplicates, setDuplicates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [view, setView] = useState('dashboard');
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedId, setExpandedId] = useState(null);
  
  const [filters, setFilters] = useState({
    min_price: 0,
    max_price: 25000000,
    min_rooms: 0,
    min_size: 0
  });
  
  const [showFilters, setShowFilters] = useState(false);

  // Fetch Stats
  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await fetch(`${API_URL}/api/stats`);
        if (!response.ok) throw new Error('Stats laden fehlgeschlagen');
        const data = await response.json();
        setStats(data.statistiken);
      } catch (err) {
        setError(err.message);
      }
    };
    
    fetchStats();
    const interval = setInterval(fetchStats, 30000); // Refresh alle 30s
    return () => clearInterval(interval);
  }, []);

  // Fetch Immobilien
  useEffect(() => {
    const fetchImmobilien = async () => {
      setLoading(true);
      try {
        let url = `${API_URL}/api/immobilien?limit=100`;
        if (searchTerm) {
          url += `&search=${encodeURIComponent(searchTerm)}`;
        }
        
        const response = await fetch(url);
        if (!response.ok) throw new Error('Immobilien laden fehlgeschlagen');
        const data = await response.json();
        setImmobilien(data.immobilien);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    
    fetchImmobilien();
  }, [searchTerm]);

  // Fetch Duplicates
  useEffect(() => {
    const fetchDuplicates = async () => {
      try {
        const response = await fetch(`${API_URL}/api/duplicates?limit=50`);
        if (!response.ok) throw new Error('Duplikate laden fehlgeschlagen');
        const data = await response.json();
        setDuplicates(data.duplicates);
      } catch (err) {
        setError(err.message);
      }
    };
    
    if (view === 'duplicates') {
      fetchDuplicates();
    }
  }, [view]);

  // Apply Filter
  const handleApplyFilter = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        min_price: filters.min_price,
        max_price: filters.max_price,
        min_rooms: filters.min_rooms,
        min_size: filters.min_size
      });
      
      const response = await fetch(`${API_URL}/api/filter?${params}`);
      if (!response.ok) throw new Error('Filter fehlgeschlagen');
      const data = await response.json();
      setImmobilien(data.immobilien);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const formatPrice = (price) => {
    return new Intl.NumberFormat('de-AT', {
      style: 'currency',
      currency: 'EUR',
      maximumFractionDigits: 0
    }).format(price);
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    const now = new Date();
    const diffHours = Math.floor((now - date) / 3600000);
    
    if (diffHours < 24) {
      return `vor ${diffHours}h`;
    }
    return date.toLocaleDateString('de-AT');
  };

  const StatCard = ({ icon: Icon, label, value, color }) => (
    <div className="bg-white rounded-lg shadow p-6 border-l-4" style={{ borderLeftColor: color }}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-gray-600 text-sm">{label}</p>
          <p className="text-2xl font-bold mt-1">{value}</p>
        </div>
        <Icon className="w-8 h-8" style={{ color }} />
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto p-4">
        
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">🏠 Immobilien-Tracker</h1>
          <p className="text-gray-600 mt-2">Automatisierte Überwachung von Immobilienmärkten</p>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <p className="text-red-800">⚠️ {error}</p>
          </div>
        )}

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <StatCard 
            icon={Home} 
            label="Aktive Angebote" 
            value={stats.total.toLocaleString('de-AT')} 
            color="#3b82f6" 
          />
          <StatCard 
            icon={TrendingUp} 
            label="Neu heute" 
            value={stats.neu_heute} 
            color="#10b981" 
          />
          <StatCard 
            icon={DollarSign} 
            label="Ø Preis" 
            value={formatPrice(stats.durchschnittspreis)} 
            color="#f59e0b" 
          />
          <StatCard 
            icon={AlertCircle} 
            label="Duplikate" 
            value={stats.duplikate} 
            color="#ef4444" 
          />
        </div>

        {/* Navigation */}
        <div className="bg-white rounded-lg shadow mb-6 p-4 flex gap-4">
          <button
            onClick={() => setView('dashboard')}
            className={`px-4 py-2 rounded font-medium transition ${
              view === 'dashboard'
                ? 'bg-blue-500 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Dashboard
          </button>
          <button
            onClick={() => setView('list')}
            className={`px-4 py-2 rounded font-medium transition ${
              view === 'list'
                ? 'bg-blue-500 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Alle Angebote ({stats.total})
          </button>
          <button
            onClick={() => setView('duplicates')}
            className={`px-4 py-2 rounded font-medium transition ${
              view === 'duplicates'
                ? 'bg-blue-500 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Duplikate ({stats.duplikate})
          </button>
        </div>

        {/* Filter Panel */}
        {(view === 'list' || view === 'dashboard') && (
          <div className="bg-white rounded-lg shadow p-4 mb-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold flex items-center gap-2">
                <Filter className="w-4 h-4" />
                Filter
              </h3>
              <button
                onClick={() => setShowFilters(!showFilters)}
                className="text-sm text-blue-600 hover:text-blue-800"
              >
                {showFilters ? 'Ausblenden' : 'Anzeigen'}
              </button>
            </div>

            {showFilters && (
              <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Min Preis (€)</label>
                  <input
                    type="number"
                    value={filters.min_price}
                    onChange={(e) => setFilters({ ...filters, min_price: parseFloat(e.target.value) })}
                    className="w-full px-3 py-2 border rounded text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Max Preis (€)</label>
                  <input
                    type="number"
                    value={filters.max_price}
                    onChange={(e) => setFilters({ ...filters, max_price: parseFloat(e.target.value) })}
                    className="w-full px-3 py-2 border rounded text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Min Zimmer</label>
                  <input
                    type="number"
                    value={filters.min_rooms}
                    onChange={(e) => setFilters({ ...filters, min_rooms: parseInt(e.target.value) })}
                    className="w-full px-3 py-2 border rounded text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Min Größe (m²)</label>
                  <input
                    type="number"
                    value={filters.min_size}
                    onChange={(e) => setFilters({ ...filters, min_size: parseFloat(e.target.value) })}
                    className="w-full px-3 py-2 border rounded text-sm"
                  />
                </div>
                <button
                  onClick={handleApplyFilter}
                  className="bg-blue-500 text-white px-4 py-2 rounded font-medium hover:bg-blue-600 self-end"
                >
                  Anwenden
                </button>
              </div>
            )}

            {(view === 'list') && (
              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">Suche</label>
                <div className="flex">
                  <Search className="w-4 h-4 absolute mt-3 ml-3 text-gray-400" />
                  <input
                    type="text"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    placeholder="Adresse, Titel..."
                    className="w-full pl-9 px-3 py-2 border rounded text-sm"
                  />
                </div>
              </div>
            )}
          </div>
        )}

        {/* Content */}
        {loading && view === 'list' ? (
          <div className="text-center py-8">
            <p className="text-gray-600">Laden...</p>
          </div>
        ) : view === 'dashboard' ? (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold mb-4">Letzte Updates</h2>
            <div className="space-y-4">
              {immobilien.slice(0, 10).map((immo) => (
                <div key={immo.id} className="border rounded-lg p-4 hover:bg-gray-50 transition">
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <h3 className="font-semibold text-gray-900">{immo.titel}</h3>
                      <p className="text-sm text-gray-600 mt-1">{immo.adresse}</p>
                      {immo.zimmer && <p className="text-xs text-gray-500 mt-1">🛏️ {immo.zimmer} Zimmer | 📐 {immo.flaeche}m²</p>}
                    </div>
                    <div className="text-right">
                      <p className="font-bold text-lg text-blue-600">{formatPrice(immo.preis)}</p>
                      <p className="text-xs text-gray-500 mt-1">{formatDate(immo.aktualisiert_am)}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : view === 'list' ? (
          <div className="space-y-4">
            {immobilien.map((immo) => (
              <div
                key={immo.id}
                className="bg-white rounded-lg shadow p-4 hover:shadow-lg transition cursor-pointer"
                onClick={() => setExpandedId(expandedId === immo.id ? null : immo.id)}
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900">{immo.titel}</h3>
                    <p className="text-sm text-gray-600 mt-1">{immo.adresse}</p>
                    {immo.zimmer && <p className="text-xs text-gray-500 mt-1">🛏️ {immo.zimmer} Zimmer | 📐 {immo.flaeche}m²</p>}
                  </div>
                  <div className="text-right">
                    <p className="font-bold text-lg text-blue-600">{formatPrice(immo.preis)}</p>
                    <p className="text-xs text-gray-500 mt-1">{formatDate(immo.aktualisiert_am)}</p>
                  </div>
                </div>

                {expandedId === immo.id && (
                  <div className="mt-4 pt-4 border-t space-y-2 text-sm text-gray-600">
                    <a href={immo.url} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline block">
                      → Zur Anzeige (willhaben.at)
                    </a>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : view === 'duplicates' ? (
          <div className="space-y-4">
            {duplicates.length === 0 ? (
              <div className="bg-white rounded-lg shadow p-6 text-center text-gray-600">
                Keine Duplikate gefunden
              </div>
            ) : (
              duplicates.map((dup) => (
                <div key={dup.id} className="bg-white rounded-lg shadow overflow-hidden">
                  <div className="bg-red-50 px-4 py-3 border-b border-red-200">
                    <h3 className="font-semibold text-red-900">
                      {dup.immo1.titel}
                    </h3>
                    <p className="text-sm text-red-700 mt-1">
                      Ähnlichkeitsgrad: {dup.similarity}%
                    </p>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4 p-4">
                    {[dup.immo1, dup.immo2].map((immo, idx) => (
                      <div key={idx} className="border rounded p-3 bg-gray-50">
                        <p className="text-xs text-gray-500">Angebot #{idx + 1}</p>
                        <p className="font-bold text-lg mt-1">{formatPrice(immo.preis)}</p>
                        <p className="text-sm text-gray-600 mt-2">{immo.adresse}</p>
                      </div>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
        ) : null}

        {/* Footer */}
        <div className="mt-8 text-center text-sm text-gray-600">
          <p>Letzte Aktualisierung: {new Date().toLocaleString('de-AT')}</p>
        </div>
      </div>
    </div>
  );
}
