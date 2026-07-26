'use client'

import Link from 'next/link'

import { AppShell } from '@/components/layout/app-shell'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const ITEMS = [
  {
    href: '/lottery/admin/control-center/motor/table1',
    title: 'Tabla 1',
    desc: 'Relaciona cada número con sus compañeros principales.',
  },
  {
    href: '/lottery/admin/control-center/motor/table2',
    title: 'Tabla 2',
    desc: 'Confirma y amplía las relaciones encontradas en Tabla 1.',
  },
  {
    href: '/lottery/admin/control-center/motor/patron',
    title: 'Patrón Matriz',
    desc: 'Muestra las conexiones utilizadas para comparar números y comportamiento histórico.',
  },
] as const

export default function LotteryPatronesPage() {
  return (
    <AppShell>
      <div className="mx-auto max-w-5xl space-y-6 p-6">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-sm font-medium text-blue-700">Lottery IA</p>
            <h1 className="text-2xl font-semibold text-slate-900">Patrones y tablas</h1>
            <p className="mt-1 max-w-2xl text-sm text-slate-600">
              Consulte las relaciones del motor. Al hacer clic en un número podrá abrir su análisis completo.
            </p>
          </div>
          <Button variant="outline" asChild>
            <Link href="/lottery">Volver al inicio</Link>
          </Button>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {ITEMS.map((item) => (
            <Card key={item.href} className="border-blue-100">
              <CardHeader>
                <CardTitle className="text-lg text-blue-900">{item.title}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-sm text-slate-600">{item.desc}</p>
                <Button className="bg-blue-600 hover:bg-blue-700" asChild>
                  <Link href={item.href}>Abrir</Link>
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </AppShell>
  )
}
