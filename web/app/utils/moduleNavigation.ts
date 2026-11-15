import type { UiMobileTabBarLink, UiMobileTabBarNavigation, UiMobileTabBarPagePlacement } from '~/types/UiMobileTabBar'
import type { DlhModule, DlhModulePrimaryCta, UiSidebarGroup, UiSidebarLink } from '~/types/UiSidebar'
import {
  MOBILE_TAB_BAR_CAPTIONS,
  MOBILE_TAB_BAR_MAXIMUM_PHONE_LINK_COUNT,
  MOBILE_TAB_BAR_MAXIMUM_TABLET_LINK_COUNT,
  MOBILE_TAB_BAR_NOTIFICATIONS_LINK,
  MOBILE_TAB_BAR_SHARED_PROSPECTING_PAGE_PATHS,
  MOBILE_TAB_BAR_WEBSITES_MAIN_ACTION,
  MOBILE_TAB_BAR_WEBSITES_PAGE_PLACEMENTS,
} from '~/constants/mobileTabBar'
import { WEBSITES_DASHBOARD_PATH, WEBSITES_MODULE_KEY } from '~/constants/productModules'

/** What the dashboard shows of a module's menu: the sidebar's groups and the installed app's bottom bar. */
export class ModuleNavigation {
  private constructor() {}

  /**
   * Whether a path is a page or one of its sub-pages.
   * @param path - The path to test.
   * @param pagePath - The page's path.
   * @returns True when `path` is `pagePath` or sits under it.
   */
  static isPathAtOrUnder(path: string, pagePath: string): boolean {
    return path === pagePath || path.startsWith(`${pagePath}/`)
  }

  /**
   * The one path of a menu that the current page lights up: the longest match, so a sub-page never lights its parent.
   * @param currentPath - The current route's path.
   * @param menuPaths - Every path of the menu.
   * @returns The elected path, or null when the page belongs to none.
   */
  static electActivePath(currentPath: string, menuPaths: string[]): string | null {
    let electedPath: string | null = null

    for (const menuPath of menuPaths) {
      const isLongerThanElectedPath: boolean = electedPath === null || menuPath.length > electedPath.length

      if (ModuleNavigation.isMenuPathOpen(currentPath, menuPath) && isLongerThanElectedPath) {
        electedPath = menuPath
      }
    }
    return electedPath
  }

  /**
   * A product module's menu without the link to the websites dashboard, whose figures are not the module's.
   * @param groups - The groups the module declares.
   * @returns The groups that still hold a link; a module's own dashboard, at its own path, stays.
   */
  static removeWebsitesDashboardLink(groups: UiSidebarGroup[]): UiSidebarGroup[] {
    return groups
      .map(
        (group: UiSidebarGroup): UiSidebarGroup => ({
          ...group,
          links: group.links.filter((link: UiSidebarLink): boolean => link.to !== WEBSITES_DASHBOARD_PATH),
        }),
      )
      .filter((group: UiSidebarGroup): boolean => group.links.length > 0)
  }

  /**
   * A module's bottom bar, read from its menu.
   * @param module - The module the user has open.
   * @returns The bar's links in order, and the action of its middle button, whose page is never also a tab.
   */
  static buildTabBar(module: DlhModule): UiMobileTabBarNavigation {
    const menuLinks: UiSidebarLink[] = module.navGroups.flatMap((group: UiSidebarGroup): UiSidebarLink[] => group.links)

    if (module.key === WEBSITES_MODULE_KEY) {
      return {
        links: ModuleNavigation.buildWebsitesTabBarLinks(menuLinks),
        mainAction: MOBILE_TAB_BAR_WEBSITES_MAIN_ACTION,
      }
    }
    const mainAction: DlhModulePrimaryCta | null = module.tabBarMainAction ?? module.primaryCta
    const tabLinks: UiSidebarLink[] = menuLinks.filter((link: UiSidebarLink): boolean => link.to !== mainAction?.to)
    return {
      links: ModuleNavigation.buildProductModuleTabBarLinks(tabLinks, module.home),
      mainAction,
    }
  }

  /**
   * Whether the current page is a menu's page or one of its sub-pages (the websites dashboard has no sub-page).
   * @param currentPath - The current route's path.
   * @param menuPath - A path of the menu.
   * @returns True when the menu's page is the one open.
   */
  private static isMenuPathOpen(currentPath: string, menuPath: string): boolean {
    if (menuPath === WEBSITES_DASHBOARD_PATH) {
      return currentPath === menuPath
    }
    return ModuleNavigation.isPathAtOrUnder(currentPath, menuPath)
  }

  /**
   * The websites module's bar: the pages its placements list, in their order.
   * @param menuLinks - The links of the websites menu.
   * @returns The bar's links, each shown on the phone or kept for the tablet as its placement says.
   */
  private static buildWebsitesTabBarLinks(menuLinks: UiSidebarLink[]): UiMobileTabBarLink[] {
    const tabBarLinks: UiMobileTabBarLink[] = []

    for (const placement of MOBILE_TAB_BAR_WEBSITES_PAGE_PLACEMENTS) {
      const tabBarLink: UiMobileTabBarLink | null = ModuleNavigation.findTabBarLink(menuLinks, placement)

      if (tabBarLink) {
        tabBarLinks.push(tabBarLink)
      }
    }
    return tabBarLinks
  }

  /**
   * A product module's bar: its own pages, the notifications, then the shared prospecting pages its menu holds.
   * @param menuLinks - The links of the module's menu.
   * @param modulePath - The module's home, under which its own pages sit.
   * @returns The bar's links; the phone shows the first ones, which always include the notifications.
   */
  private static buildProductModuleTabBarLinks(menuLinks: UiSidebarLink[], modulePath: string): UiMobileTabBarLink[] {
    const modulePagePaths: string[] = menuLinks
      .map((link: UiSidebarLink): string => link.to)
      .filter((path: string): boolean => ModuleNavigation.isPathAtOrUnder(path, modulePath))
    const modulePageCountBeforeNotifications: number = MOBILE_TAB_BAR_MAXIMUM_PHONE_LINK_COUNT - 1
    const orderedPaths: string[] = [
      ...modulePagePaths.slice(0, modulePageCountBeforeNotifications),
      MOBILE_TAB_BAR_NOTIFICATIONS_LINK.to,
      ...modulePagePaths.slice(modulePageCountBeforeNotifications),
      ...MOBILE_TAB_BAR_SHARED_PROSPECTING_PAGE_PATHS,
    ]
    const tabBarLinks: UiMobileTabBarLink[] = []

    for (const path of orderedPaths) {
      const placement: UiMobileTabBarPagePlacement = {
        to: path,
        isShownOnPhone: tabBarLinks.length < MOBILE_TAB_BAR_MAXIMUM_PHONE_LINK_COUNT,
      }
      const tabBarLink: UiMobileTabBarLink | null = ModuleNavigation.findTabBarLink(menuLinks, placement)

      if (tabBarLink && tabBarLinks.length < MOBILE_TAB_BAR_MAXIMUM_TABLET_LINK_COUNT) {
        tabBarLinks.push(tabBarLink)
      }
    }
    return tabBarLinks
  }

  /**
   * The bar's link to a page: the notifications, or a page of the module's menu.
   * @param menuLinks - The links of the module's menu.
   * @param placement - The page, and whether the phone shows it.
   * @returns The link, or null when the menu does not hold the page.
   */
  private static findTabBarLink(
    menuLinks: UiSidebarLink[],
    placement: UiMobileTabBarPagePlacement,
  ): UiMobileTabBarLink | null {
    if (placement.to === MOBILE_TAB_BAR_NOTIFICATIONS_LINK.to) {
      return { ...MOBILE_TAB_BAR_NOTIFICATIONS_LINK, isShownOnPhone: placement.isShownOnPhone }
    }
    const menuLink: UiSidebarLink | undefined = menuLinks.find(
      (link: UiSidebarLink): boolean => link.to === placement.to,
    )

    if (!menuLink) {
      return null
    }
    return {
      to: menuLink.to,
      icon: menuLink.icon,
      label: menuLink.label,
      caption: MOBILE_TAB_BAR_CAPTIONS[menuLink.to] ?? null,
      counterKey: menuLink.counterKey ?? null,
      isShownOnPhone: placement.isShownOnPhone,
    }
  }
}
