'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useEffect } from 'react'

import { AppShell } from '@/components/layout/app-shell'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { getAccessToken, getUserRole } from '@/lib/auth'
import { canAccessLotteryAdmin } from '@/lib/lottery'

const BLOCKS = [
  {
    title: 'Resultados',
    items: [
      {
        href: '/lottery/admin/sync',
        label: 'Sincronización',
        desc: 'Ejecuciones, estado de escritura y respaldo de sincronización.',
      },
      {
        href: '/lottery/admin/scheduler',
        label: 'Fuentes y scheduler',
        desc: 'Worker, ventanas horarias, bloqueos y fuentes de datos.',
      },
      {
        href: '/lottery/admin/lotteries/archivo-historico',
        label: 'Histórico técnico',
        desc: 'Inventario y mantenimiento del archivo histórico.',
      },
      {
        href: '/lottery/resultados',
        label: 'Centro de Resultados',
        desc: 'Consulta operativa de sorteos y pendientes de sync.',
      },
    ],
  },
  {
    title: 'Inteligencia artificial',
    items: [
      {
        href: '/lottery/admin/ai',
        label: 'Configuración del Chat inteligente',
        desc: 'Proveedor, modelo, herramientas y estado del agente.',
      },
      {
        href: '/lottery/admin/control-center/prompt-studio',
        label: 'Prompt Studio',
        desc: 'Prompts del sistema y funcionales versionados.',
      },
      {
        href: '/lottery/chat',
        label: 'Probar Chat inteligente',
        desc: 'Abrir una conversación de prueba con el agente.',
      },
    ],
  },
  {
    title: 'Motor',
    items: [
      {
        href: '/lottery/ia',
        label: 'Versión y estado congelado',
        desc: 'Motor v1.0, perfil activo y datos de congelamiento (solo lectura).',
      },
      {
        href: '/lottery/admin/control-center/motor/historical-audit',
        label: 'Auditoría histórica del motor',
        desc: 'Valida la lógica manual sobre el histórico sin modificar el motor.',
      },
      {
        href: '/lottery/admin/control-center/motor/auditoria',
        label: 'Auditoría por sorteo',
        desc: 'Trazabilidad técnica de confirmaciones por sorteo.',
      },
    ],
  },
  {
    title: 'Catálogos',
    items: [
      {
        href: '/lottery/admin/lotteries',
        label: 'Loterías',
        desc: 'Visibilidad, destacadas y configuración por lotería.',
      },
      {
        href: '/lottery/lotteries',
        label: 'Catálogo visible',
        desc: 'Vista de las loterías activas para el usuario.',
      },
    ],
  },
] as const

export default function LotteryAdministracionPage() {
  const router = useRouter()
  useEffect(() => {
    if (!getAccessToken()) {
      router.replace('/login?session=expired')
      return
    }
    if (!canAccessLotteryAdmin(getUserRole())) {
      router.replace('/lottery')
    }
  }, [router])

  return (
    <AppShell>
      <div className="mx-auto max-w-5xl space-y-6 p-6">
        <div>
          <p className="text-sm font-medium text-blue-700">Lottery IA</p>
          <h1 className="text-2xl font-semibold text-slate-900">Administración</h1>
          <p className="mt-1 text-sm text-slate-600">
            Herramientas técnicas y de mantenimiento. Requiere permisos de administrador.
          </p>
        </div>
        <div className="space-y-6">
          {BLOCKS.map((block) => (
            <section key={block.title} className="space-y-3">
              <h2 className="text-lg font-semibold text-blue-900">{block.title}</h2>
              <div className="grid gap-3 md:grid-cols-2">
                {block.items.map((item) => (
                  <Link key={item.href} href={item.href} className="block">
                    <Card className="h-full border-blue-100 transition hover:border-blue-300 hover:shadow-sm">
                      <CardHeader className="pb-2">
                        <CardTitle className="text-base text-slate-900">{item.label}</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <p className="text-sm text-slate-600">{item.desc}</p>
                      </CardContent>
                    </Card>
                  </Link>
                ))}
              </div>
            </section>
          ))}
        </div>
      </div>
    </AppShell>
  )
}
