import React, { useState, useMemo } from 'react';
import { PieChart, Pie, Cell, Tooltip as RechartsTooltip, ResponsiveContainer } from 'recharts';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as BarTooltip, Legend } from 'recharts';

const MAPA_COLORES = {
  "Sumar": "#E51C55",       
  "PSOE": "#ef4444", // Red            
  "Vox": "#22c55e",  // Green           
  "PP": "#1E90FF",          
  "Mesa": "#8b4513", // SaddleBrown   
  "ERC": "#FFD700",         
  "EH Bildu": "#40e0d0", // Turquoise
  "PNV": "#228B22" // ForestGreen
};

export default function DashboardEstadisticas({ data }) {
  const [filtroPartido, setFiltroPartido] = useState('Todos');

  if (!data || data.error) {
    return (
      <div className="flex justify-center items-center h-64 text-red-500 bg-red-500/10 rounded-xl">
        <p>{data?.error || "Error al cargar las estadísticas."}</p>
      </div>
    );
  }

  const { barras, tarta } = data;

  // Extraer partidos únicos para los filtros
  const partidosDisponibles = ['Todos', ...Array.from(new Set(barras.map(b => b.partido)))];

  // Preparar datos para el PieChart
  const datosTarta = tarta.map(item => ({
    name: item.partido,
    value: item.duracion,
    color: MAPA_COLORES[item.partido] || '#808080'
  }));

  // Filtrar y preparar datos para el BarChart
  const barrasFiltradas = useMemo(() => {
    let filtradas = barras;
    if (filtroPartido !== 'Todos') {
      filtradas = barras.filter(b => b.partido === filtroPartido);
    }
    // Formatear para el gráfico
    return filtradas.map(b => ({
      nombre: b.nombre,
      partido: b.partido,
      porcentaje_global: Number(b.porcentaje_global.toFixed(1)),
      porcentaje_relativo: Number(b.porcentaje_relativo.toFixed(1)),
      color: MAPA_COLORES[b.partido] || '#808080'
    }));
  }, [barras, filtroPartido]);

  // Tooltip personalizado para la tarta
  const CustomPieTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-[#1C1C1E]/90 backdrop-blur-md p-3 rounded-lg border border-white/10 text-white shadow-xl">
          <p className="font-semibold text-sm mb-1">{data.name}</p>
          <p className="text-xs text-white/70">Tiempo: {data.value.toFixed(1)} segundos</p>
        </div>
      );
    }
    return null;
  };

  // Tooltip personalizado para las barras
  const CustomBarTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-[#1C1C1E]/90 backdrop-blur-md p-3 rounded-lg border border-white/10 text-white shadow-xl">
          <p className="font-semibold text-sm mb-1">{label} <span className="text-xs font-normal text-white/50">({data.partido})</span></p>
          <p className="text-xs text-[#0A84FF]">{payload[0].name}: {payload[0].value}%</p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="w-full h-full flex flex-col p-2 space-y-6 overflow-y-auto custom-scrollbar">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-white/90">Análisis de Tiempos de Habla</h2>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 min-h-[400px]">
        {/* TARTA: Resumen por partidos */}
        <div className="bg-white/5 rounded-2xl p-4 border border-white/10 flex flex-col items-center justify-center">
          <h3 className="text-sm font-medium text-white/70 mb-4 w-full text-center">Distribución Total por Partido</h3>
          <div className="w-full h-64 relative">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={datosTarta}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                  stroke="none"
                >
                  {datosTarta.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <RechartsTooltip content={<CustomPieTooltip />} />
              </PieChart>
            </ResponsiveContainer>
            {/* Leyenda manual bajo la tarta */}
            <div className="mt-2 w-full flex flex-wrap justify-center gap-2">
              {datosTarta.map((entry, index) => (
                 <div key={index} className="flex items-center text-xs text-white/60">
                   <span className="w-2 h-2 rounded-full mr-1" style={{backgroundColor: entry.color}}></span>
                   {entry.name}
                 </div>
              ))}
            </div>
          </div>
        </div>

        {/* BARRAS: Detalle por ponente */}
        <div className="lg:col-span-2 bg-white/5 rounded-2xl p-4 border border-white/10 flex flex-col">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6">
            <h3 className="text-sm font-medium text-white/70">
              {filtroPartido === 'Todos' ? 'Intervención Global (%)' : `Intervención Interna en ${filtroPartido} (%)`}
            </h3>
            
            <div className="flex gap-2 mt-2 sm:mt-0 flex-wrap">
              {partidosDisponibles.map(partido => (
                <button
                  key={partido}
                  onClick={() => setFiltroPartido(partido)}
                  className={`px-3 py-1 text-xs rounded-full transition-colors ${
                    filtroPartido === partido
                      ? 'bg-[#0A84FF] text-white font-medium shadow-md shadow-[#0A84FF]/20'
                      : 'bg-white/5 text-white/60 hover:bg-white/10 border border-white/10'
                  }`}
                >
                  {partido}
                </button>
              ))}
            </div>
          </div>

          <div className="w-full h-64 flex-1">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={barrasFiltradas}
                margin={{ top: 10, right: 10, left: -20, bottom: 20 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" vertical={false} />
                <XAxis 
                  dataKey="nombre" 
                  stroke="#ffffff50" 
                  tick={{fill: '#ffffff50', fontSize: 10}}
                  angle={-45}
                  textAnchor="end"
                  height={60}
                  interval={0}
                />
                <YAxis 
                  stroke="#ffffff50" 
                  tick={{fill: '#ffffff50', fontSize: 10}} 
                  domain={[0, 100]}
                />
                <BarTooltip cursor={{fill: 'rgba(255,255,255,0.05)'}} content={<CustomBarTooltip />} />
                <Bar 
                  dataKey={filtroPartido === 'Todos' ? "porcentaje_global" : "porcentaje_relativo"} 
                  name={filtroPartido === 'Todos' ? "% Global" : "% Relativo"} 
                  radius={[4, 4, 0, 0]}
                >
                  {barrasFiltradas.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
