import type { PresenterVideoExampleDemo, PresenterVideoModuleAdapter } from '~/types/PresenterVideoConfig'
import type { PresenterVideoTake } from '~/types/PresenterVideoTake'
import type { DemoSite, DemoSiteListResponse } from '~/services/demoSiteService'
import type { PreviewVideoResult } from '~/services/storyblokSidecarService'
import { buildDefaultScript, WEBSITES_SCRIPT_STORAGE_KEY } from '~/composables/useProspectionScript'
import { WEBSITES_MODULE_KEY } from '~/constants/productModules'
import { WEBSITES_PRESENTER_VIDEO_WORDING } from '~/constants/presenterVideoWordings'
import { SITE_VIDEO_BUILD_PHASES } from '~/constants/videoBuildPhases'
import { DemoSiteService } from '~/services/demoSiteService'
import { StoryblokSidecarService } from '~/services/storyblokSidecarService'
import { PresenterVideoTimings } from '~/utils/presenterVideoTimings'

/**
 * The user's demo sites that can be filmed: live, with the Storyblok space the editor sequence opens.
 * @returns Them as example demos.
 */
async function loadSiteExampleDemos(): Promise<PresenterVideoExampleDemo[]> {
  const response: DemoSiteListResponse = await DemoSiteService.listDemoSites()
  return response.items
    .filter(
      (site: DemoSite): boolean =>
        site.status === 'active' && Boolean(site.demo_url) && Boolean(site.storyblok_editor_url),
    )
    .map((site: DemoSite): PresenterVideoExampleDemo => ({ id: site.id, slug: site.slug, name: site.business_name }))
}

/**
 * Render a take on a demo site with the desktop app; nothing is published.
 * @param demoSiteId - The site filmed.
 * @param take - The take montaged, with the cut points to use.
 * @returns The rendered mp4, or why it could not be made.
 */
function renderSitePreview(demoSiteId: number, take: PresenterVideoTake): Promise<PreviewVideoResult> {
  return StoryblokSidecarService.buildPreviewVideo(demoSiteId, PresenterVideoTimings.siteBuildTimings(take), take.id)
}

export const WEBSITES_PRESENTER_VIDEO_ADAPTER: PresenterVideoModuleAdapter = {
  moduleKey: WEBSITES_MODULE_KEY,
  sectionAnchorId: null,
  wording: WEBSITES_PRESENTER_VIDEO_WORDING,
  buildPhases: SITE_VIDEO_BUILD_PHASES,
  scriptStorageKey: WEBSITES_SCRIPT_STORAGE_KEY,
  fieldIdPrefix: 'video',
  middleLayout: { kind: 'site-split' },
  buildDefaultScript,
  renderPreview: renderSitePreview,
  loadExampleDemos: loadSiteExampleDemos,
}
