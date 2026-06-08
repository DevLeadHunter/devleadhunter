<template>
  <div>
    <!-- Hero Section -->
    <section class="relative overflow-hidden pt-32 pb-24 md:pt-40 md:pb-32">
      <div class="relative z-10 container mx-auto px-4 md:px-6 lg:px-8">
        <div class="mx-auto max-w-5xl text-center">
          <!-- Main Heading -->
          <h1
            class="mb-6 text-3xl leading-tight font-bold tracking-tight text-[#f9f9f9] md:text-4xl md:leading-tight lg:text-5xl"
          >
            {{ $t('hero.title') }}
            <span class="mt-3 block text-[#f9f9f9]">
              {{ $t('hero.titleHighlight') }}
            </span>
          </h1>

          <!-- Subheading -->
          <p class="mx-auto mb-10 max-w-3xl text-base leading-relaxed font-light text-[#8b949e] md:text-lg">
            {{ $t('hero.subtitle') }}
          </p>

          <!-- CTA Buttons -->
          <div class="mb-16 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <NuxtLink
              :to="localePath('/signup')"
              class="btn-primary min-h-[44px] w-full flex-1 px-6 py-3 text-sm font-medium sm:min-h-[52px] sm:w-auto sm:flex-initial sm:px-8 sm:py-4 sm:text-base"
            >
              {{ $t('hero.ctaPrimary') }}
            </NuxtLink>
            <a
              href="#features"
              class="btn-secondary min-h-[44px] w-full flex-1 px-6 py-3 text-sm font-medium sm:min-h-[52px] sm:w-auto sm:flex-initial sm:px-8 sm:py-4 sm:text-base"
              @click.prevent="scrollToSection('#features')"
            >
              {{ $t('hero.ctaSecondary') }}
            </a>
          </div>
        </div>
      </div>
    </section>

    <!-- Stats Section -->
    <section class="bg-[#050505] py-20 md:py-28">
      <div class="container mx-auto px-4 md:px-6 lg:px-8">
        <div class="mx-auto max-w-4xl">
          <div class="grid grid-cols-1 gap-12 md:grid-cols-3 md:gap-16">
            <div class="animate-fadeInUp text-center" style="animation-delay: 0.1s">
              <div class="mb-3 text-3xl font-bold text-[#f9f9f9] md:text-4xl">1000+</div>
              <div class="text-base font-medium text-[#8b949e]">{{ $t('hero.stats.prospects') }}</div>
            </div>
            <div class="animate-fadeInUp text-center" style="animation-delay: 0.2s">
              <div class="mb-3 text-3xl font-bold text-[#f9f9f9] md:text-4xl">50+</div>
              <div class="text-base font-medium text-[#8b949e]">{{ $t('hero.stats.developers') }}</div>
            </div>
            <div class="animate-fadeInUp text-center" style="animation-delay: 0.3s">
              <div class="mb-3 text-3xl font-bold text-[#f9f9f9] md:text-4xl">95%</div>
              <div class="text-base font-medium text-[#8b949e]">{{ $t('hero.stats.satisfaction') }}</div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Main Features Section -->
    <section id="features" class="bg-[#050505] py-32 md:py-40">
      <div class="container mx-auto px-4 md:px-6 lg:px-8">
        <div class="mx-auto max-w-7xl space-y-32">
          <!-- Feature 1: Recherche -->
          <div class="grid grid-cols-1 items-center gap-16 md:grid-cols-2 md:gap-20">
            <div class="animate-slideInLeft">
              <div
                class="mb-8 inline-flex items-center gap-2 rounded-full border border-[#30363d]/30 bg-[#1a1a1a]/50 px-4 py-2"
              >
                <i class="fa-solid fa-search text-sm text-[#8b949e]"></i>
                <span class="text-sm font-medium text-[#8b949e]">{{ $t('features.search.badge') }}</span>
              </div>
              <h2 class="mb-6 text-xl font-bold tracking-tight text-[#f9f9f9] md:text-2xl lg:text-3xl">
                {{ $t('features.search.heading') }}
              </h2>
              <p class="mb-8 text-sm leading-relaxed font-light text-[#8b949e]">
                {{ $t('features.search.descriptionFull') }}
              </p>
              <ul class="space-y-4">
                <li class="flex items-start gap-3">
                  <i class="fa-solid fa-check mt-1 text-base text-[#2BAD5F]"></i>
                  <span class="text-base font-light text-[#8b949e]">{{ $t('features.search.feature1') }}</span>
                </li>
                <li class="flex items-start gap-3">
                  <i class="fa-solid fa-check mt-1 text-base text-[#2BAD5F]"></i>
                  <span class="text-base font-light text-[#8b949e]">{{ $t('features.search.feature2') }}</span>
                </li>
                <li class="flex items-start gap-3">
                  <i class="fa-solid fa-check mt-1 text-base text-[#2BAD5F]"></i>
                  <span class="text-base font-light text-[#8b949e]">{{ $t('features.search.feature3') }}</span>
                </li>
                <li class="flex items-start gap-3">
                  <i class="fa-solid fa-check mt-1 text-base text-[#2BAD5F]"></i>
                  <span class="text-base font-light text-[#8b949e]">{{ $t('features.search.feature4') }}</span>
                </li>
              </ul>
            </div>
            <div class="animate-slideInRight rounded-xl border border-[#30363d] bg-[#1a1a1a] p-3 md:p-6">
              <div class="space-y-4">
                <div
                  class="flex items-center gap-4 rounded-lg border border-[#30363d] bg-[#050505] p-4 transition-colors hover:border-[#30363d]/70"
                >
                  <i class="fa-solid fa-building text-lg text-[#8b949e]"></i>
                  <div>
                    <div class="text-base font-medium text-[#f9f9f9]">Restaurant Le Gourmet</div>
                    <div class="text-sm font-light text-[#8b949e]">Paris, 75001</div>
                  </div>
                </div>
                <div
                  class="flex items-center gap-4 rounded-lg border border-[#30363d] bg-[#050505] p-4 transition-colors hover:border-[#30363d]/70"
                >
                  <i class="fa-solid fa-building text-lg text-[#8b949e]"></i>
                  <div>
                    <div class="text-base font-medium text-[#f9f9f9]">Salon de coiffure Style</div>
                    <div class="text-sm font-light text-[#8b949e]">Lyon, 69001</div>
                  </div>
                </div>
                <div
                  class="flex items-center gap-4 rounded-lg border border-[#30363d] bg-[#050505] p-4 transition-colors hover:border-[#30363d]/70"
                >
                  <i class="fa-solid fa-building text-lg text-[#8b949e]"></i>
                  <div>
                    <div class="text-base font-medium text-[#f9f9f9]">Cabinet médical Santé</div>
                    <div class="text-sm font-light text-[#8b949e]">Marseille, 13001</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Feature 2: Campagnes -->
          <div class="grid grid-cols-1 items-center gap-16 md:grid-cols-2 md:gap-20">
            <div class="animate-slideInRight order-2 md:order-1">
              <div class="rounded-xl border border-[#30363d] bg-[#1a1a1a] p-3 md:p-6">
                <div class="space-y-4">
                  <div
                    class="rounded-lg border border-[#30363d] bg-[#050505] p-6 transition-colors hover:border-[#30363d]/70"
                  >
                    <div class="mb-3 text-base font-semibold text-[#f9f9f9]">
                      {{ $t('features.campaigns.campaignExample') }}
                    </div>
                    <div
                      class="flex flex-col items-start gap-3 text-sm font-light text-[#8b949e] md:flex-row md:items-center md:gap-6"
                    >
                      <span><i class="fa-solid fa-users mr-2"></i> 25 {{ $t('features.campaigns.prospects') }}</span>
                      <span><i class="fa-solid fa-envelope mr-2"></i> 20 {{ $t('features.campaigns.sent') }}</span>
                      <span><i class="fa-solid fa-check mr-2"></i> 5 {{ $t('features.campaigns.replies') }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div class="animate-slideInLeft order-1 md:order-2">
              <div
                class="mb-8 inline-flex items-center gap-2 rounded-full border border-[#30363d]/30 bg-[#1a1a1a]/50 px-4 py-2"
              >
                <i class="fa-solid fa-envelope text-sm text-[#8b949e]"></i>
                <span class="text-sm font-medium text-[#8b949e]">{{ $t('features.campaigns.badge') }}</span>
              </div>
              <h2 class="mb-6 text-xl font-bold tracking-tight text-[#f9f9f9] md:text-2xl lg:text-3xl">
                {{ $t('features.campaigns.heading') }}
              </h2>
              <p class="mb-8 text-sm leading-relaxed font-light text-[#8b949e]">
                {{ $t('features.campaigns.descriptionFull') }}
              </p>
              <ul class="space-y-4">
                <li class="flex items-start gap-3">
                  <i class="fa-solid fa-check mt-1 text-base text-[#2BAD5F]"></i>
                  <span class="text-base font-light text-[#8b949e]">{{ $t('features.campaigns.feature1') }}</span>
                </li>
                <li class="flex items-start gap-3">
                  <i class="fa-solid fa-check mt-1 text-base text-[#2BAD5F]"></i>
                  <span class="text-base font-light text-[#8b949e]">{{ $t('features.campaigns.feature2') }}</span>
                </li>
                <li class="flex items-start gap-3">
                  <i class="fa-solid fa-check mt-1 text-base text-[#2BAD5F]"></i>
                  <span class="text-base font-light text-[#8b949e]">{{ $t('features.campaigns.feature3') }}</span>
                </li>
                <li class="flex items-start gap-3">
                  <i class="fa-solid fa-check mt-1 text-base text-[#2BAD5F]"></i>
                  <span class="text-base font-light text-[#8b949e]">{{ $t('features.campaigns.feature4') }}</span>
                </li>
              </ul>
            </div>
          </div>

          <!-- Feature 3: Gestion -->
          <div class="grid grid-cols-1 items-center gap-16 md:grid-cols-2 md:gap-20">
            <div class="animate-slideInLeft">
              <div
                class="mb-8 inline-flex items-center gap-2 rounded-full border border-[#30363d]/30 bg-[#1a1a1a]/50 px-4 py-2"
              >
                <i class="fa-solid fa-database text-sm text-[#8b949e]"></i>
                <span class="text-sm font-medium text-[#8b949e]">{{ $t('features.management.badge') }}</span>
              </div>
              <h2 class="mb-6 text-xl font-bold tracking-tight text-[#f9f9f9] md:text-2xl lg:text-3xl">
                {{ $t('features.management.heading') }}
              </h2>
              <p class="mb-8 text-sm leading-relaxed font-light text-[#8b949e]">
                {{ $t('features.management.descriptionFull') }}
              </p>
              <ul class="space-y-4">
                <li class="flex items-start gap-3">
                  <i class="fa-solid fa-check mt-1 text-base text-[#2BAD5F]"></i>
                  <span class="text-base font-light text-[#8b949e]">{{ $t('features.management.feature1') }}</span>
                </li>
                <li class="flex items-start gap-3">
                  <i class="fa-solid fa-check mt-1 text-base text-[#2BAD5F]"></i>
                  <span class="text-base font-light text-[#8b949e]">{{ $t('features.management.feature2') }}</span>
                </li>
                <li class="flex items-start gap-3">
                  <i class="fa-solid fa-check mt-1 text-base text-[#2BAD5F]"></i>
                  <span class="text-base font-light text-[#8b949e]">{{ $t('features.management.feature3') }}</span>
                </li>
                <li class="flex items-start gap-3">
                  <i class="fa-solid fa-check mt-1 text-base text-[#2BAD5F]"></i>
                  <span class="text-base font-light text-[#8b949e]">{{ $t('features.management.feature4') }}</span>
                </li>
              </ul>
            </div>
            <div class="animate-slideInRight rounded-xl border border-[#30363d] bg-[#1a1a1a] p-3 md:p-6">
              <div class="space-y-4">
                <div
                  class="rounded-lg border border-[#30363d] bg-[#050505] p-6 transition-colors hover:border-[#30363d]/70"
                >
                  <div class="mb-3 flex items-center justify-between">
                    <div class="text-base font-semibold text-[#f9f9f9]">
                      {{ $t('features.management.myProspects') }}
                    </div>
                    <span class="rounded-lg bg-[#2BAD5F]/10 px-3 py-1 text-sm font-medium text-[#2BAD5F]">125</span>
                  </div>
                  <div class="text-sm font-light text-[#8b949e]">{{ $t('features.management.allContacts') }}</div>
                </div>
                <div
                  class="rounded-lg border border-[#30363d] bg-[#050505] p-6 transition-colors hover:border-[#30363d]/70"
                >
                  <div class="mb-3 flex items-center justify-between">
                    <div class="text-base font-semibold text-[#f9f9f9]">
                      {{ $t('features.management.activeCampaigns') }}
                    </div>
                    <span class="rounded-lg bg-[#30363d]/50 px-3 py-1 text-sm font-medium text-[#8b949e]">3</span>
                  </div>
                  <div class="text-sm font-light text-[#8b949e]">{{ $t('features.management.trackCampaigns') }}</div>
                </div>
              </div>
            </div>
          </div>

          <!-- Feature 4: Statistiques -->
          <div class="grid grid-cols-1 items-center gap-16 md:grid-cols-2 md:gap-20">
            <div class="animate-slideInRight order-2 md:order-1">
              <div class="rounded-xl border border-[#30363d] bg-[#1a1a1a] p-3 md:p-6">
                <div class="space-y-4">
                  <div
                    class="rounded-lg border border-[#30363d] bg-[#050505] p-6 transition-colors hover:border-[#30363d]/70"
                  >
                    <div class="mb-2 text-sm font-medium text-[#8b949e]">{{ $t('features.analytics.openRate') }}</div>
                    <div class="text-2xl font-bold text-[#f9f9f9]">68%</div>
                  </div>
                  <div
                    class="rounded-lg border border-[#30363d] bg-[#050505] p-6 transition-colors hover:border-[#30363d]/70"
                  >
                    <div class="mb-2 text-sm font-medium text-[#8b949e]">{{ $t('features.analytics.replyRate') }}</div>
                    <div class="text-2xl font-bold text-[#f9f9f9]">24%</div>
                  </div>
                  <div
                    class="rounded-lg border border-[#30363d] bg-[#050505] p-6 transition-colors hover:border-[#30363d]/70"
                  >
                    <div class="mb-2 text-sm font-medium text-[#8b949e]">{{ $t('features.analytics.converted') }}</div>
                    <div class="text-2xl font-bold text-[#2BAD5F]">12</div>
                  </div>
                </div>
              </div>
            </div>
            <div class="animate-slideInLeft order-1 md:order-2">
              <div
                class="mb-8 inline-flex items-center gap-2 rounded-full border border-[#30363d]/30 bg-[#1a1a1a]/50 px-4 py-2"
              >
                <i class="fa-solid fa-chart-line text-sm text-[#8b949e]"></i>
                <span class="text-sm font-medium text-[#8b949e]">{{ $t('features.analytics.badge') }}</span>
              </div>
              <h2 class="mb-6 text-xl font-bold tracking-tight text-[#f9f9f9] md:text-2xl lg:text-3xl">
                {{ $t('features.analytics.heading') }}
              </h2>
              <p class="mb-8 text-sm leading-relaxed font-light text-[#8b949e]">
                {{ $t('features.analytics.descriptionFull') }}
              </p>
              <ul class="space-y-4">
                <li class="flex items-start gap-3">
                  <i class="fa-solid fa-check mt-1 text-base text-[#2BAD5F]"></i>
                  <span class="text-base font-light text-[#8b949e]">{{ $t('features.analytics.feature1') }}</span>
                </li>
                <li class="flex items-start gap-3">
                  <i class="fa-solid fa-check mt-1 text-base text-[#2BAD5F]"></i>
                  <span class="text-base font-light text-[#8b949e]">{{ $t('features.analytics.feature2') }}</span>
                </li>
                <li class="flex items-start gap-3">
                  <i class="fa-solid fa-check mt-1 text-base text-[#2BAD5F]"></i>
                  <span class="text-base font-light text-[#8b949e]">{{ $t('features.analytics.feature3') }}</span>
                </li>
                <li class="flex items-start gap-3">
                  <i class="fa-solid fa-check mt-1 text-base text-[#2BAD5F]"></i>
                  <span class="text-base font-light text-[#8b949e]">{{ $t('features.analytics.feature4') }}</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Pricing Section -->
    <section id="pricing" class="bg-[#050505] py-32 md:py-40">
      <div class="container mx-auto px-4 md:px-6 lg:px-8">
        <div class="mb-20 text-center">
          <h2 class="mb-5 text-2xl font-bold tracking-tight text-[#f9f9f9] md:text-3xl lg:text-4xl">
            {{ $t('pricing.title') }}
          </h2>
          <p class="mx-auto max-w-2xl text-base font-light text-[#8b949e] md:text-lg">
            {{ $t('pricing.subtitle') }}
          </p>
        </div>

        <div v-if="isLoading" class="mx-auto max-w-4xl">
          <div class="animate-pulse rounded-lg border border-[#30363d]/50 bg-[#1a1a1a] p-8">
            <div class="mb-4 h-6 w-1/3 rounded bg-[#21262d]"></div>
            <div class="mb-6 h-4 w-2/3 rounded bg-[#21262d]"></div>
            <div class="grid grid-cols-2 gap-4 md:grid-cols-4">
              <div class="h-20 rounded bg-[#21262d]"></div>
              <div class="h-20 rounded bg-[#21262d]"></div>
              <div class="h-20 rounded bg-[#21262d]"></div>
              <div class="h-20 rounded bg-[#21262d]"></div>
            </div>
          </div>
        </div>

        <div v-else-if="creditSettings" class="mx-auto max-w-5xl">
          <!-- Credit Info Card -->
          <div class="rounded-2xl border border-[#30363d]/30 bg-transparent p-4 md:p-12">
            <h3 class="mb-4 text-xl font-bold text-[#f9f9f9] md:text-2xl">{{ $t('pricing.creditsTitle') }}</h3>
            <p class="mb-10 text-sm font-light text-[#8b949e]">{{ $t('pricing.creditsSubtitle') }}</p>

            <div class="mb-10 grid grid-cols-1 gap-6 md:grid-cols-2">
              <div
                class="rounded-xl border border-[#30363d]/30 bg-transparent p-6 transition-all hover:border-[#30363d]/50"
              >
                <div class="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-[#21262d]/50">
                  <i class="fa-solid fa-search text-lg text-[#f9f9f9]"></i>
                </div>
                <h4 class="mb-2 text-lg font-semibold text-[#f9f9f9]">{{ $t('pricing.search.title') }}</h4>
                <p class="text-base font-light text-[#8b949e]">{{ $t('pricing.search.description') }}</p>
              </div>
              <div
                class="rounded-xl border border-[#30363d]/30 bg-transparent p-6 transition-all hover:border-[#30363d]/50"
              >
                <div class="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-[#21262d]/50">
                  <i class="fa-solid fa-envelope text-lg text-[#f9f9f9]"></i>
                </div>
                <h4 class="mb-2 text-lg font-semibold text-[#f9f9f9]">{{ $t('pricing.email.title') }}</h4>
                <p class="text-base font-light text-[#8b949e]">{{ $t('pricing.email.description') }}</p>
              </div>
            </div>

            <!-- Credit Pricing Details -->
            <div class="grid grid-cols-1 gap-6 border-t border-[#30363d]/30 pt-10 sm:grid-cols-2 md:grid-cols-4">
              <div class="text-center">
                <div class="mb-2 text-sm font-medium text-[#8b949e]">{{ $t('pricing.pricePerCredit') }}</div>
                <div class="text-xl font-bold text-[#f9f9f9]">€{{ creditSettings.price_per_credit.toFixed(2) }}</div>
              </div>
              <div class="text-center">
                <div class="mb-2 text-sm font-medium text-[#8b949e]">{{ $t('pricing.creditsPerSearch') }}</div>
                <div class="text-xl font-bold text-[#f9f9f9]">{{ creditSettings.credits_per_search }}</div>
              </div>
              <div class="text-center">
                <div class="mb-2 text-sm font-medium text-[#8b949e]">{{ $t('pricing.creditsPerResult') }}</div>
                <div class="text-xl font-bold text-[#f9f9f9]">{{ creditSettings.credits_per_result }}</div>
              </div>
              <div class="text-center">
                <div class="mb-2 text-sm font-medium text-[#8b949e]">{{ $t('pricing.creditsPerEmail') }}</div>
                <div class="text-xl font-bold text-[#f9f9f9]">{{ creditSettings.credits_per_email }}</div>
              </div>
            </div>

            <!-- Free Credits & Minimum -->
            <div class="mt-10 grid grid-cols-1 gap-6 border-t border-[#30363d]/30 pt-10 md:grid-cols-2">
              <div class="rounded-xl border border-[#30363d]/30 bg-transparent p-6">
                <div class="mb-2 text-sm font-medium text-[#8b949e]">{{ $t('pricing.freeCredits') }}</div>
                <div class="text-2xl font-bold text-[#2BAD5F]">{{ creditSettings.free_credits_on_signup }}</div>
              </div>
              <div class="rounded-xl border border-[#30363d]/30 bg-transparent p-6">
                <div class="mb-2 text-sm font-medium text-[#8b949e]">{{ $t('pricing.minPurchase') }}</div>
                <div class="text-2xl font-bold text-[#f9f9f9]">{{ creditSettings.minimum_credits_purchase }}</div>
              </div>
            </div>
          </div>
        </div>

        <div v-else class="mx-auto max-w-4xl">
          <div class="rounded-lg border border-[#30363d]/50 bg-[#1a1a1a] p-8 text-center">
            <p class="text-[#8b949e]">Failed to load credit settings. Please try again later.</p>
          </div>
        </div>
      </div>
    </section>

    <!-- How It Works Section -->
    <section class="bg-[#1a1a1a] py-32 md:py-40">
      <div class="container mx-auto px-4 md:px-6 lg:px-8">
        <div class="mb-20 text-center">
          <h2 class="mb-5 text-2xl font-bold tracking-tight text-[#f9f9f9] md:text-3xl lg:text-4xl">
            {{ $t('howItWorks.title') }}
          </h2>
          <p class="mx-auto max-w-2xl text-sm font-light text-[#8b949e] md:text-base">
            {{ $t('howItWorks.subtitle') }}
          </p>
        </div>

        <div class="mx-auto max-w-5xl px-2 md:px-0">
          <div class="space-y-20">
            <!-- Step 1 -->
            <div class="animate-fadeInUp flex flex-col items-start gap-10 md:flex-row" style="animation-delay: 0.1s">
              <div
                class="flex h-16 w-16 flex-shrink-0 items-center justify-center rounded-2xl bg-[#21262d]/50 text-2xl font-bold text-[#f9f9f9]"
              >
                1
              </div>
              <div class="flex-1">
                <h3 class="mb-4 text-lg font-semibold text-[#f9f9f9] md:text-xl">{{ $t('howItWorks.step1.title') }}</h3>
                <p class="text-sm leading-relaxed font-light text-[#8b949e]">
                  {{ $t('howItWorks.step1.description') }}
                </p>
              </div>
            </div>

            <!-- Step 2 -->
            <div class="animate-fadeInUp flex flex-col items-start gap-10 md:flex-row" style="animation-delay: 0.2s">
              <div
                class="flex h-16 w-16 flex-shrink-0 items-center justify-center rounded-2xl bg-[#21262d]/50 text-2xl font-bold text-[#f9f9f9]"
              >
                2
              </div>
              <div class="flex-1">
                <h3 class="mb-4 text-lg font-semibold text-[#f9f9f9] md:text-xl">{{ $t('howItWorks.step2.title') }}</h3>
                <p class="text-sm leading-relaxed font-light text-[#8b949e]">
                  {{ $t('howItWorks.step2.description') }}
                </p>
              </div>
            </div>

            <!-- Step 3 -->
            <div class="animate-fadeInUp flex flex-col items-start gap-10 md:flex-row" style="animation-delay: 0.3s">
              <div
                class="flex h-16 w-16 flex-shrink-0 items-center justify-center rounded-2xl bg-[#21262d]/50 text-2xl font-bold text-[#f9f9f9]"
              >
                3
              </div>
              <div class="flex-1">
                <h3 class="mb-4 text-lg font-semibold text-[#f9f9f9] md:text-xl">{{ $t('howItWorks.step3.title') }}</h3>
                <p class="text-sm leading-relaxed font-light text-[#8b949e]">
                  {{ $t('howItWorks.step3.description') }}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Additional Features Grid -->
    <section class="bg-[#050505] py-32 md:py-40">
      <div class="container mx-auto px-4 md:px-6 lg:px-8">
        <div class="mb-20 text-center">
          <h2 class="mb-5 text-xl font-bold tracking-tight text-[#f9f9f9] md:text-2xl lg:text-3xl">
            {{ $t('features.more.title') }}
          </h2>
        </div>
        <div class="mx-auto grid max-w-7xl grid-cols-1 gap-10 md:grid-cols-2 lg:grid-cols-3">
          <div
            class="animate-fadeInUp rounded-xl border border-[#30363d] bg-[#1a1a1a] p-4 transition-all duration-300 hover:scale-105 hover:border-[#30363d]/70 md:p-8"
            style="animation-delay: 0.1s"
          >
            <i class="fa-solid fa-coins mb-4 text-xl text-[#8b949e]"></i>
            <h3 class="mb-3 text-base font-semibold text-[#f9f9f9]">{{ $t('features.more.credits.title') }}</h3>
            <p class="text-sm leading-relaxed font-light text-[#8b949e]">
              {{ $t('features.more.credits.description') }}
            </p>
          </div>
          <div
            class="animate-fadeInUp rounded-xl border border-[#30363d] bg-[#1a1a1a] p-4 transition-all duration-300 hover:scale-105 hover:border-[#30363d]/70 md:p-8"
            style="animation-delay: 0.2s"
          >
            <i class="fa-solid fa-envelope-circle-check mb-4 text-xl text-[#8b949e]"></i>
            <h3 class="mb-3 text-base font-semibold text-[#f9f9f9]">{{ $t('features.more.emailAccounts.title') }}</h3>
            <p class="text-sm leading-relaxed font-light text-[#8b949e]">
              {{ $t('features.more.emailAccounts.description') }}
            </p>
          </div>
          <div
            class="animate-fadeInUp rounded-xl border border-[#30363d] bg-[#1a1a1a] p-4 transition-all duration-300 hover:scale-105 hover:border-[#30363d]/70 md:p-8"
            style="animation-delay: 0.3s"
          >
            <i class="fa-solid fa-file-lines mb-4 text-xl text-[#8b949e]"></i>
            <h3 class="mb-3 text-base font-semibold text-[#f9f9f9]">{{ $t('features.more.templates.title') }}</h3>
            <p class="text-sm leading-relaxed font-light text-[#8b949e]">
              {{ $t('features.more.templates.description') }}
            </p>
          </div>
          <div
            class="animate-fadeInUp rounded-xl border border-[#30363d] bg-[#1a1a1a] p-4 transition-all duration-300 hover:scale-105 hover:border-[#30363d]/70 md:p-8"
            style="animation-delay: 0.4s"
          >
            <i class="fa-solid fa-headset mb-4 text-xl text-[#8b949e]"></i>
            <h3 class="mb-3 text-base font-semibold text-[#f9f9f9]">{{ $t('features.more.support.title') }}</h3>
            <p class="text-sm leading-relaxed font-light text-[#8b949e]">
              {{ $t('features.more.support.description') }}
            </p>
          </div>
          <div
            class="animate-fadeInUp rounded-xl border border-[#30363d] bg-[#1a1a1a] p-4 transition-all duration-300 hover:scale-105 hover:border-[#30363d]/70 md:p-8"
            style="animation-delay: 0.5s"
          >
            <i class="fa-solid fa-mobile-screen mb-4 text-xl text-[#8b949e]"></i>
            <h3 class="mb-3 text-base font-semibold text-[#f9f9f9]">{{ $t('features.more.responsive.title') }}</h3>
            <p class="text-sm leading-relaxed font-light text-[#8b949e]">
              {{ $t('features.more.responsive.description') }}
            </p>
          </div>
          <div
            class="animate-fadeInUp rounded-xl border border-[#30363d] bg-[#1a1a1a] p-4 transition-all duration-300 hover:scale-105 hover:border-[#30363d]/70 md:p-8"
            style="animation-delay: 0.6s"
          >
            <i class="fa-solid fa-lock mb-4 text-xl text-[#8b949e]"></i>
            <h3 class="mb-3 text-base font-semibold text-[#f9f9f9]">{{ $t('features.more.security.title') }}</h3>
            <p class="text-sm leading-relaxed font-light text-[#8b949e]">
              {{ $t('features.more.security.description') }}
            </p>
          </div>
        </div>
      </div>
    </section>

    <!-- FAQ Section -->
    <section class="bg-[#050505] py-32 md:py-40">
      <div class="container mx-auto px-4 md:px-6 lg:px-8">
        <div class="mx-auto max-w-4xl">
          <div class="mb-20 text-center">
            <h2 class="mb-5 text-2xl font-bold text-[#f9f9f9] md:text-3xl">
              {{ $t('pricing.faq.title') }}
            </h2>
          </div>
          <div class="space-y-4">
            <div
              v-for="(faq, index) in faqs"
              :key="index"
              class="overflow-hidden rounded-lg border border-[#30363d] bg-[#1a1a1a]"
            >
              <button
                class="flex w-full items-center justify-between p-6 text-left transition-colors hover:bg-[#21262d]"
                @click="toggleFaq(index)"
              >
                <h3 class="pr-4 text-lg font-semibold text-[#f9f9f9]">
                  {{ faq.question }}
                </h3>
                <i
                  :class="[
                    'fa-solid flex-shrink-0 transition-transform',
                    openFaqs.has(index) ? 'fa-chevron-up' : 'fa-chevron-down',
                    openFaqs.has(index) ? 'text-[#f9f9f9]' : 'text-[#8b949e]',
                  ]"
                ></i>
              </button>
              <div v-show="openFaqs.has(index)" class="px-6 pb-6">
                <p class="text-base leading-relaxed font-light text-[#8b949e]">
                  {{ faq.answer }}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- CTA Section -->
    <section class="bg-[#050505] py-32 md:py-40">
      <div class="container mx-auto px-4 md:px-6 lg:px-8">
        <div class="mx-auto max-w-4xl text-center">
          <h2 class="mb-6 text-2xl font-bold tracking-tight text-[#f9f9f9] md:text-3xl lg:text-4xl">
            {{ $t('cta.title') }}
          </h2>
          <p class="mx-auto mb-10 max-w-2xl text-base leading-relaxed font-light text-[#8b949e] md:text-lg">
            {{ $t('cta.subtitle') }}
          </p>
          <div class="flex flex-col justify-center gap-4 sm:flex-row">
            <NuxtLink
              :to="localePath('/signup')"
              class="btn-primary min-h-[44px] w-full flex-1 px-6 py-3 text-sm font-medium sm:min-h-[52px] sm:w-auto sm:flex-initial sm:px-8 sm:py-4 sm:text-base"
            >
              {{ $t('cta.primary') }}
            </NuxtLink>
            <a
              href="#pricing"
              class="btn-secondary min-h-[44px] w-full flex-1 px-6 py-3 text-sm font-medium sm:min-h-[52px] sm:w-auto sm:flex-initial sm:px-8 sm:py-4 sm:text-base"
              @click.prevent="scrollToSection('#pricing')"
            >
              {{ $t('cta.secondary') }}
            </a>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import type { CreditSettings } from '~/types'
import type { Ref } from 'vue'
import { ref, onMounted } from 'vue'
import * as creditSettingsService from '~/services/creditSettingsService'

/**
 * Landing page - Marketing page with hero, features, pricing, and CTA sections
 */
definePageMeta({
  layout: 'marketing',
  // Desktop app: skip the landing and go to the dashboard (web keeps the landing).
  middleware: ['desktop-redirect'],
})

const localePath = useLocalePath()
const { t } = useI18n()

/**
 * Credit settings state
 */
const creditSettings: Ref<CreditSettings | null> = ref(null)
const isLoading: Ref<boolean> = ref(true)

/**
 * FAQ state
 */
const openFaqs: Ref<Set<number>> = ref(new Set([0])) // First FAQ open by default

/**
 * FAQ data
 */
const faqs = computed(() => [
  {
    question: t('pricing.faq.q1'),
    answer: t('pricing.faq.a1'),
  },
  {
    question: t('pricing.faq.q2'),
    answer: t('pricing.faq.a2'),
  },
  {
    question: t('pricing.faq.q3'),
    answer: t('pricing.faq.a3'),
  },
])

/**
 * Toggle FAQ
 */
const toggleFaq = (index: number): void => {
  if (openFaqs.value.has(index)) {
    openFaqs.value.delete(index)
  } else {
    openFaqs.value.add(index)
  }
}

/**
 * Load credit settings from API
 */
const loadCreditSettings = async (): Promise<void> => {
  try {
    isLoading.value = true
    creditSettings.value = await creditSettingsService.getCreditSettings()
  } catch (error) {
    console.error('Failed to load credit settings:', error)
  } finally {
    isLoading.value = false
  }
}

/**
 * Smooth scroll to section
 */
const scrollToSection = (selector: string): void => {
  const element = document.querySelector(selector)
  if (element) {
    const headerOffset = 80
    const elementPosition = element.getBoundingClientRect().top
    const offsetPosition = elementPosition + window.pageYOffset - headerOffset

    window.scrollTo({
      top: offsetPosition,
      behavior: 'smooth',
    })
  }
}

/**
 * Initialize
 */
onMounted(async () => {
  await loadCreditSettings()
})

// SEO Meta
useHead({
  title: () => t('hero.title') + ' ' + t('hero.titleHighlight') + ' - devleadhunter',
  meta: [
    {
      name: 'description',
      content: () => t('hero.subtitle'),
    },
  ],
})
</script>
