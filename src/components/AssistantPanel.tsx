import React, { useMemo, useState } from 'react';
import { AlertCircle, Bot, CheckCircle2, FileText, Loader2, Send, Sparkles } from 'lucide-react';
import { AssistantChatMessage, AssistantQueryResponse } from '../types';
import { assistantApi } from '../services/apiClient';

type ChatEntry = AssistantChatMessage & {
  response?: AssistantQueryResponse;
  isError?: boolean;
};

const QUICK_PROMPTS = [
  'En que fase esta el proyecto?',
  'Interpreta la corrida actual',
  'Que modelo predictivo esta seleccionado?',
  'Que puedo comparar en fase 8?',
  'Como se usaran Aiken, Cronbach y KR-20?',
];

export const AssistantPanel: React.FC = () => {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<ChatEntry[]>([
    {
      role: 'assistant',
      content:
        'Estoy listo para ayudarte con el estado del proyecto, el dataset NYC EMS, los modelos entrenados, la corrida activa y los limites metodologicos.',
      timestamp: new Date().toISOString(),
    },
  ]);
  const [isLoading, setIsLoading] = useState(false);

  const conversation = useMemo(
    () =>
      messages
        .filter((message) => !message.isError)
        .map(({ role, content, timestamp }) => ({ role, content, timestamp }))
        .slice(-8),
    [messages]
  );

  const sendMessage = async (messageText: string) => {
    const trimmed = messageText.trim();
    if (!trimmed || isLoading) return;

    const userMessage: ChatEntry = {
      role: 'user',
      content: trimmed,
      timestamp: new Date().toISOString(),
    };

    setMessages((current) => [...current, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await assistantApi.query({
        message: trimmed,
        conversation,
      });

      setMessages((current) => [
        ...current,
        {
          role: 'assistant',
          content: response.answer,
          timestamp: response.generated_at,
          response,
        },
      ]);
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          role: 'assistant',
          content: 'No pude conectarme con el endpoint del asistente. Revisa que el servidor principal este ejecutandose.',
          timestamp: new Date().toISOString(),
          isError: true,
        },
      ]);
      console.warn('Assistant request failed:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const latestResponse = [...messages].reverse().find((message) => message.response)?.response;

  return (
    <section className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="bg-white border border-slate-200 rounded-lg shadow-xs overflow-hidden">
          <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-900 text-white">
                <Bot className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-sm font-semibold text-slate-900">Asistente Analitico EMS</h2>
                <p className="text-xs text-slate-500">LangGraph conectado a documentacion, modelos y corrida activa</p>
              </div>
            </div>
            <span className="inline-flex items-center gap-1 rounded-md border border-emerald-200 bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-700">
              <CheckCircle2 className="h-3.5 w-3.5" />
              Operativo
            </span>
          </div>

          <div className="h-[520px] overflow-y-auto bg-slate-50 px-4 py-4">
            <div className="space-y-4">
              {messages.map((message, index) => {
                const isUser = message.role === 'user';
                return (
                  <div key={`${message.timestamp}-${index}`} className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
                    <div
                      className={`max-w-[82%] rounded-lg border px-4 py-3 text-sm leading-6 ${
                        isUser
                          ? 'border-slate-900 bg-slate-900 text-white'
                          : message.isError
                            ? 'border-rose-200 bg-rose-50 text-rose-900'
                            : 'border-slate-200 bg-white text-slate-800'
                      }`}
                    >
                      <p className="whitespace-pre-line">{message.content}</p>

                      {message.response && (
                        <div className="mt-3 space-y-2 border-t border-slate-200 pt-3 text-xs text-slate-500">
                          <div className="flex flex-wrap gap-2">
                            <span className="rounded-md bg-slate-100 px-2 py-1">Intencion: {message.response.intent}</span>
                            <span
                              className={`rounded-md px-2 py-1 ${
                                message.response.status === 'not_ready'
                                  ? 'bg-amber-100 text-amber-800'
                                  : 'bg-emerald-100 text-emerald-800'
                              }`}
                            >
                              Estado: {message.response.status}
                            </span>
                          </div>

                          {message.response.evidence.length > 0 && (
                            <div className="space-y-1">
                              {message.response.evidence.map((item) => (
                                <div key={`${item.source}-${item.title}`} className="flex gap-2">
                                  <FileText className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                                  <span>
                                    <strong>{item.source}</strong>: {item.excerpt}
                                  </span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}

              {isLoading && (
                <div className="flex justify-start">
                  <div className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Consultando grafo...
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="border-t border-slate-200 bg-white p-3">
            <div className="mb-3 flex flex-wrap gap-2">
              {QUICK_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => void sendMessage(prompt)}
                  disabled={isLoading}
                  className="rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {prompt}
                </button>
              ))}
            </div>

            <form
              className="flex gap-2"
              onSubmit={(event) => {
                event.preventDefault();
                void sendMessage(input);
              }}
            >
              <input
                value={input}
                onChange={(event) => setInput(event.target.value)}
                placeholder="Pregunta sobre fases, modelos, simulacion o limites actuales..."
                className="min-w-0 flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
              />
              <button
                type="submit"
                disabled={isLoading || !input.trim()}
                className="inline-flex items-center gap-2 rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
              >
                <Send className="h-4 w-4" />
                Enviar
              </button>
            </form>
          </div>
        </div>

        <aside className="space-y-4">
          <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-xs">
            <div className="mb-3 flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-indigo-600" />
              <h3 className="text-sm font-semibold text-slate-900">Capacidades actuales</h3>
            </div>
            <ul className="space-y-2 text-xs leading-5 text-slate-600">
              {(latestResponse?.available_capabilities || [
                'Consultar documentacion y estado del pipeline.',
                'Interpretar modelos entrenados y corrida activa.',
                'Explicar alcance y limites actuales.',
              ]).map((item) => (
                <li key={item} className="flex gap-2">
                  <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-600" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="bg-white border border-amber-200 rounded-lg p-4 shadow-xs">
            <div className="mb-3 flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-amber-600" />
              <h3 className="text-sm font-semibold text-slate-900">Aun no disponible</h3>
            </div>
            <ul className="space-y-2 text-xs leading-5 text-slate-600">
              {(latestResponse?.pending_capabilities || [
                'Conclusiones causales u operativas reales.',
                'Resultados de Aiken, Cronbach y KR-20 con participantes reales.',
                'Despliegue multiusuario con auditoria transaccional.',
              ]).map((item) => (
                <li key={item} className="flex gap-2">
                  <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-500" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="bg-slate-900 rounded-lg p-4 text-xs leading-5 text-slate-200 shadow-xs">
            <p className="font-semibold text-white">Flujo LangGraph</p>
            <p className="mt-2">
              El grafo clasifica la pregunta, consulta documentos, lee artefactos locales y usa el estado persistido de simulacion.
            </p>
            {latestResponse && (
              <p className="mt-2 text-slate-300">
                Ultima traza: {latestResponse.graph_trace.join(' -> ')}
              </p>
            )}
          </div>
        </aside>
      </div>
    </section>
  );
};
