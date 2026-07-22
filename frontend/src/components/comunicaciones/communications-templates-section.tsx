"use client";

import { Plus, Trash2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type Template = {
  id: string;
  name: string;
  body: string;
  channel: string;
};

const STORAGE_KEY = "jaios-comms-templates";

const DEFAULT_TEMPLATES: Template[] = [
  { id: "1", name: "Saludo comercial", body: "Buenos días, gracias por contactarnos. ¿En qué podemos ayudarle?", channel: "whatsapp" },
  { id: "2", name: "Seguimiento cotización", body: "Le escribo para dar seguimiento a la cotización enviada. Quedamos atentos.", channel: "whatsapp" },
  { id: "3", name: "Solicitud documentos", body: "Para continuar el proceso, necesitamos los documentos indicados. Gracias.", channel: "email" },
];

function loadTemplates(): Template[] {
  if (typeof window === "undefined") return DEFAULT_TEMPLATES;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as Template[]) : DEFAULT_TEMPLATES;
  } catch {
    return DEFAULT_TEMPLATES;
  }
}

export function CommunicationsTemplatesSection() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [name, setName] = useState("");
  const [body, setBody] = useState("");

  useEffect(() => {
    setTemplates(loadTemplates());
  }, []);

  const persist = useCallback((next: Template[]) => {
    setTemplates(next);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  }, []);

  const addTemplate = () => {
    if (!name.trim() || !body.trim()) return;
    persist([
      ...templates,
      { id: crypto.randomUUID(), name: name.trim(), body: body.trim(), channel: "whatsapp" },
    ]);
    setName("");
    setBody("");
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Nueva plantilla</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Input placeholder="Nombre de la plantilla" value={name} onChange={(e) => setName(e.target.value)} />
          <textarea
            className="min-h-[100px] w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
            placeholder="Texto del mensaje…"
            value={body}
            onChange={(e) => setBody(e.target.value)}
          />
          <Button size="sm" onClick={addTemplate}>
            <Plus className="mr-2 h-4 w-4" />
            Guardar plantilla
          </Button>
        </CardContent>
      </Card>

      <div className="grid gap-3 md:grid-cols-2">
        {templates.map((t) => (
          <Card key={t.id}>
            <CardHeader className="flex flex-row items-start justify-between pb-2">
              <CardTitle className="text-sm font-medium">{t.name}</CardTitle>
              <Button
                size="icon"
                variant="ghost"
                className="h-8 w-8 text-destructive"
                onClick={() => persist(templates.filter((x) => x.id !== t.id))}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </CardHeader>
            <CardContent>
              <p className="whitespace-pre-wrap text-sm text-muted-foreground">{t.body}</p>
              <p className="mt-2 text-[10px] uppercase text-muted-foreground">{t.channel}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
