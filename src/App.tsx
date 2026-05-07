/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Bar,
  Cell
} from 'recharts';
import { format } from 'date-fns';
import { Activity, ArrowUpRight, ArrowDownRight, RefreshCw, BarChart2 } from 'lucide-react';

interface OhlcData {
  time: number;
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  isUp: boolean;
}

export default function App() {
  const [data, setData] = useState<OhlcData[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [currentPrice, setCurrentPrice] = useState<number | null>(null);
  const [priceChange, setPriceChange] = useState<number | null>(null);
  const [priceChangePercent, setPriceChangePercent] = useState<number | null>(null);

  const fetchMarketData = async () => {
    setLoading(true);
    setError(null);
    try {
      // Fetch 1D OHLC data from Kraken for BTC/USD
      const response = await axios.get('https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval=1440');
      
      if (response.data.error && response.data.error.length > 0) {
        throw new Error(response.data.error[0]);
      }

      const result = response.data.result;
      const pairKey = Object.keys(result).find(key => key !== 'last');
      
      if (!pairKey) {
        throw new Error('Data format error');
      }

      const rawData = result[pairKey];
      
      const formattedData: OhlcData[] = rawData.map((item: any) => {
        const timestamp = item[0] * 1000;
        const open = parseFloat(item[1]);
        const high = parseFloat(item[2]);
        const low = parseFloat(item[3]);
        const close = parseFloat(item[4]);
        const volume = parseFloat(item[6]);
        
        return {
          time: timestamp,
          date: format(new Date(timestamp), 'MMM dd, yyyy'),
          open,
          high,
          low,
          close,
          volume,
          isUp: close >= open
        };
      });

      // Keep only last 100 days for better visualization
      const recentData = formattedData.slice(-100);
      setData(recentData);
      
      if (recentData.length >= 2) {
        const last = recentData[recentData.length - 1];
        const prev = recentData[recentData.length - 2];
        const change = last.close - prev.close;
        const changePercent = (change / prev.close) * 100;
        
        setCurrentPrice(last.close);
        setPriceChange(change);
        setPriceChangePercent(changePercent);
      }
      
      setLastUpdated(new Date());
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Failed to fetch market data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMarketData();
    // Auto refresh every 5 minutes
    const interval = setInterval(fetchMarketData, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val);
  };

  // Custom Tooltip for Recharts
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-gray-900 border border-gray-800 p-4 rounded-lg shadow-xl text-sm">
          <p className="text-gray-400 mb-2">{data.date}</p>
          <div className="grid grid-cols-2 gap-x-4 gap-y-2">
            <span className="text-gray-500">Open:</span>
            <span className="text-white font-mono">{formatCurrency(data.open)}</span>
            <span className="text-gray-500">High:</span>
            <span className="text-white font-mono">{formatCurrency(data.high)}</span>
            <span className="text-gray-500">Low:</span>
            <span className="text-white font-mono">{formatCurrency(data.low)}</span>
            <span className="text-gray-500">Close:</span>
            <span className={data.isUp ? "text-green-400 font-mono" : "text-red-400 font-mono"}>
              {formatCurrency(data.close)}
            </span>
            <span className="text-gray-500">Volume:</span>
            <span className="text-white font-mono">{data.volume.toFixed(2)} BTC</span>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="min-h-screen bg-black text-white font-sans selection:bg-blue-500/30">
      {/* Header */}
      <header className="border-b border-white/10 bg-black/50 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center">
              <Activity className="w-5 h-5 text-white" />
            </div>
            <h1 className="text-xl font-bold tracking-tight">TradeDash</h1>
          </div>
          
          <button 
            onClick={fetchMarketData}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-1.5 rounded-md hover:bg-white/5 text-sm text-gray-300 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            <span className="hidden sm:inline">Refrescar</span>
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        
        {/* Market Overview */}
        <div className="mb-8 p-6 rounded-2xl bg-gradient-to-br from-gray-900 to-black border border-white/10">
          <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <span className="px-2 py-1 rounded bg-yellow-500/10 text-yellow-500 text-xs font-semibold tracking-wider">BTC/USD</span>
                <span className="text-gray-400 text-sm flex items-center gap-1">
                  <BarChart2 className="w-4 h-4" /> 1D Timeframe
                </span>
              </div>
              <h2 className="text-4xl sm:text-5xl font-bold tracking-tight">
                {currentPrice ? formatCurrency(currentPrice) : '---'}
              </h2>
            </div>
            
            <div className="flex items-end gap-4">
              {priceChangePercent !== null && (
                <div className={`flex flex-col ${priceChangePercent >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                  <span className="text-sm text-gray-500 mb-1">Cambio 24h</span>
                  <div className="flex items-center gap-1 text-xl font-medium">
                    {priceChangePercent >= 0 ? <ArrowUpRight className="w-5 h-5" /> : <ArrowDownRight className="w-5 h-5" />}
                    <span>{Math.abs(priceChangePercent).toFixed(2)}%</span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Chart Section */}
        <div className="bg-[#0b0e14] border border-white/5 rounded-2xl p-4 sm:p-6 shadow-2xl relative">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-lg font-medium text-gray-200">Bitcoin Price Chart</h3>
            {lastUpdated && (
              <span className="text-xs text-gray-500">
                Ult. Act: {lastUpdated.toLocaleTimeString()}
              </span>
            )}
          </div>
          
          {loading && data.length === 0 ? (
            <div className="h-[400px] flex items-center justify-center">
              <div className="flex flex-col items-center gap-3">
                <RefreshCw className="w-8 h-8 text-blue-500 animate-spin" />
                <p className="text-gray-400">Cargando datos del mercado...</p>
              </div>
            </div>
          ) : error ? (
            <div className="h-[400px] flex items-center justify-center">
              <div className="text-center p-6 bg-red-500/10 border border-red-500/20 rounded-xl">
                <p className="text-red-400 mb-2">Error de conexión</p>
                <p className="text-sm text-gray-400">{error}</p>
              </div>
            </div>
          ) : (
            <div className="h-[400px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={data} margin={{ top: 10, right: 0, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#ffffff0a" vertical={false} />
                  <XAxis 
                    dataKey="date" 
                    tickFormatter={(val) => val.split(' ')[0] + ' ' + val.split(' ')[1]}
                    stroke="#ffffff40" 
                    tick={{ fill: '#ffffff60', fontSize: 12 }} 
                    minTickGap={50}
                  />
                  <YAxis 
                    yAxisId="price"
                    domain={['auto', 'auto']} 
                    stroke="#ffffff40" 
                    tick={{ fill: '#ffffff60', fontSize: 12 }} 
                    tickFormatter={(val) => '$' + val.toLocaleString()}
                    orientation="right"
                  />
                  <YAxis 
                    yAxisId="volume"
                    domain={[0, 'dataMax * 4']} 
                    hide
                  />
                  <Tooltip content={<CustomTooltip />} />
                  
                  {/* Volume Bars */}
                  <Bar 
                    yAxisId="volume"
                    dataKey="volume" 
                    fill="#3b82f6" 
                    opacity={0.3}
                  >
                    {data.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.isUp ? '#10b981' : '#ef4444'} opacity={0.2} />
                    ))}
                  </Bar>
                  
                  {/* Price Line (acting as close price) */}
                  <Line 
                    yAxisId="price"
                    type="monotone" 
                    dataKey="close" 
                    stroke="#3b82f6" 
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 4, fill: '#3b82f6', stroke: '#000', strokeWidth: 2 }}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
        
        {/* Info Section */}
        <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-5 rounded-xl bg-white/5 border border-white/5">
                <h4 className="text-gray-400 text-sm mb-1">Fuente de Datos</h4>
                <p className="font-medium text-white">Kraken Public API</p>
                <p className="text-xs text-gray-500 mt-2">Petición HTTP directa sin uso de binance / yfinance u otras librerías inestables.</p>
            </div>
            <div className="p-5 rounded-xl bg-white/5 border border-white/5">
                <h4 className="text-gray-400 text-sm mb-1">Stack Tecnológico</h4>
                <p className="font-medium text-white">React, Vite, Recharts, Tailwind</p>
                <p className="text-xs text-gray-500 mt-2">Nativamente soportado por AI Studio.</p>
            </div>
            <div className="p-5 rounded-xl bg-white/5 border border-white/5">
                <h4 className="text-gray-400 text-sm mb-1">Fase 1 completada</h4>
                <p className="font-medium text-white">Sincronización Inicial</p>
                <p className="text-xs text-gray-500 mt-2">App básica con gráfico interactivo y datos en RTLista para GH.</p>
            </div>
        </div>
      </main>
    </div>
  );
}
