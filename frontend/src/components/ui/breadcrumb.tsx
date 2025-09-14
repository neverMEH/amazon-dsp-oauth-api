import * as React from "react"
import { ChevronRight } from "lucide-react"
import { Link, useLocation } from "react-router-dom"
import { cn } from "@/lib/utils"

export interface BreadcrumbItem {
  label: string
  href?: string
  icon?: React.ComponentType<{ className?: string }>
}

interface BreadcrumbNavProps {
  items?: BreadcrumbItem[]
  className?: string
  separator?: React.ReactNode
}

const defaultSeparator = <ChevronRight className="h-4 w-4 text-muted-foreground" />

export function BreadcrumbNav({
  items,
  className,
  separator = defaultSeparator
}: BreadcrumbNavProps) {
  const location = useLocation()

  // Generate breadcrumbs from current route if items not provided
  const breadcrumbItems = React.useMemo(() => {
    if (items) return items

    const pathSegments = location.pathname.split('/').filter(Boolean)
    const generatedItems: BreadcrumbItem[] = [
      { label: 'Dashboard', href: '/dashboard' }
    ]

    // Map route segments to breadcrumb items
    const routeMap: Record<string, string> = {
      'accounts': 'Accounts',
      'settings': 'Settings',
      'connection-status': 'Connection Status',
      'oauth': 'OAuth',
      'tokens': 'Tokens',
      'auth': 'Authentication'
    }

    pathSegments.forEach((segment, index) => {
      if (segment === 'dashboard') return // Skip dashboard as it's already added

      const label = routeMap[segment] || segment.charAt(0).toUpperCase() + segment.slice(1)
      const href = index === pathSegments.length - 1
        ? undefined // Last item is current page, no href
        : '/' + pathSegments.slice(0, index + 1).join('/')

      generatedItems.push({ label, href })
    })

    return generatedItems
  }, [items, location.pathname])

  if (breadcrumbItems.length <= 1) {
    return null // Don't show breadcrumbs on dashboard
  }

  return (
    <nav
      aria-label="Breadcrumb"
      className={cn("flex items-center space-x-2 text-sm", className)}
    >
      <ol className="flex items-center space-x-2">
        {breadcrumbItems.map((item, index) => {
          const isLast = index === breadcrumbItems.length - 1
          const Icon = item.icon

          return (
            <React.Fragment key={`${item.label}-${index}`}>
              <li className="flex items-center">
                {Icon && <Icon className="mr-2 h-4 w-4" />}
                {item.href && !isLast ? (
                  <Link
                    to={item.href}
                    className="text-muted-foreground hover:text-foreground transition-colors"
                  >
                    {item.label}
                  </Link>
                ) : (
                  <span className={cn(
                    isLast ? "text-foreground font-medium" : "text-muted-foreground"
                  )}>
                    {item.label}
                  </span>
                )}
              </li>
              {!isLast && (
                <li className="select-none" aria-hidden="true">
                  {separator}
                </li>
              )}
            </React.Fragment>
          )
        })}
      </ol>
    </nav>
  )
}

// Mobile-responsive breadcrumb component
export function ResponsiveBreadcrumbNav(props: BreadcrumbNavProps) {
  return (
    <>
      {/* Desktop breadcrumbs */}
      <div className="hidden sm:block">
        <BreadcrumbNav {...props} />
      </div>

      {/* Mobile breadcrumbs - show only current and parent */}
      <div className="block sm:hidden">
        <BreadcrumbNav
          {...props}
          items={props.items ?
            props.items.length > 2
              ? [props.items[0], props.items[props.items.length - 1]]
              : props.items
            : undefined
          }
        />
      </div>
    </>
  )
}