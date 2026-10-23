import { useEffect, useState } from 'react';
import { Download, RefreshCw, Loader2, ImageOff } from 'lucide-react';
import { articleFiguresApi, type ArticleFigure } from '../services/apiClient';

export function ArticleFiguresPanel() {
  const [figures, setFigures] = useState<ArticleFigure[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  const [failedImages, setFailedImages] = useState<string[]>([]);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    setFailedImages([]);
    articleFiguresApi.list().then(data => { if (active) setFigures(data.figures); })
      .catch(() => { if (active) setError('No se pudo cargar la galeria. Revisa la conexion con el backend y la exportacion de figuras.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [attempt]);
  return <section className="space-y-6 min-w-0" aria-label="Figuras del articulo">
    <header className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-4">
      <div><h1 className="text-xl font-semibold">Figuras del articulo</h1>
        <p className="text-sm text-slate-600">Edicion de publicacion · 600 dpi · PNG y TIFF sin perdida</p></div>
      {!loading && !error && figures.length > 0 && <a href={articleFiguresApi.archive} className="inline-flex items-center gap-2 rounded bg-teal-700 px-3 py-2 text-sm font-medium text-white"><Download size={16} />Descargar todas (ZIP)</a>}
    </header>
    {loading ? <p role="status" className="flex gap-2 items-center py-12"><Loader2 className="animate-spin" size={18} />Cargando figuras...</p> : error ?
      <div role="alert" className="space-y-3"><p>{error}</p><button onClick={() => setAttempt(n => n + 1)} className="flex items-center gap-2 text-teal-700"><RefreshCw size={16} />Reintentar</button></div> : figures.length === 0 ? <p>No hay figuras publicadas.</p> :
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">{figures.map((figure, index) => <article key={figure.id} className="min-w-0 overflow-hidden rounded-lg border border-slate-200 bg-white">
        <div className="aspect-[16/10] w-full bg-white p-3 flex items-center justify-center">
          {failedImages.includes(figure.id) ? <p className="flex items-center gap-2 text-sm text-slate-500"><ImageOff size={18} />Vista previa no disponible</p> :
            <img src={articleFiguresApi.url(figure.id, 'preview')} alt={figure.title} loading="lazy" className="h-full w-full object-contain" onError={() => setFailedImages(items => [...items, figure.id])} />}
        </div>
        <div className="space-y-3 border-t border-slate-100 p-4">
          <h2 className="text-sm font-semibold">{index + 1}. {figure.title}</h2>
          <p className="text-sm text-slate-600">{figure.description}</p>
          <p className="text-xs text-slate-500">{figure.width_px} × {figure.height_px} px · {figure.dpi} dpi<br />Impresion: {figure.print_width_cm} × {figure.print_height_cm} cm</p>
          <div className="flex flex-wrap gap-3">{(['png', 'tiff'] as const).map(format => <a key={format} href={articleFiguresApi.url(figure.id, format)} className="inline-flex items-center gap-2 rounded border border-slate-300 px-3 py-2 text-xs font-semibold hover:bg-slate-50" title={`Descargar ${figure.title} en ${format.toUpperCase()} a 600 dpi`}><Download size={15} />{format.toUpperCase()} · {(figure.files[format].bytes / 1048576).toFixed(1)} MB</a>)}</div>
        </div>
      </article>)}</div>}
  </section>;
}
