<template>
  <div>
    <!-- Hero Section -->
    <section class="relative overflow-hidden pt-32 pb-24 md:pt-40 md:pb-32">
      <div class="container mx-auto px-4 md:px-6 lg:px-8 relative z-10">
        <div class="max-w-5xl mx-auto text-center">
          <!-- Main Heading -->
          <h1 class="text-3xl md:text-4xl lg:text-5xl font-bold text-[#f9f9f9] mb-6 leading-tight md:leading-tight tracking-tight">
            {{ $t('hero.title') }}
            <span class="block mt-3 text-[#f9f9f9]">
              {{ $t('hero.titleHighlight') }}
            </span>
          </h1>

          <!-- Subheading -->
          <p class="text-base md:text-lg text-[#8b949e] mb-10 max-w-3xl mx-auto leading-relaxed font-light">
            {{ $t('hero.subtitle') }}
          </p>

          <!-- CTA Buttons -->
          <div class="flex flex-col sm:flex-row gap-4 justify-center items-center mb-16">
            <NuxtLink 
              :to="localePath('/signup')" 
              class="btn-primary text-sm sm:text-base px-6 sm:px-8 py-3 sm:py-4 min-h-[44px] sm:min-h-[52px] font-medium w-full sm:w-auto flex-1 sm:flex-initial"
            >
              {{ $t('hero.ctaPrimary') }}
            </NuxtLink>
            <a 
              href="#features" 
              @click.prevent="scrollToSection('#features')"
              class="btn-secondary text-sm sm:text-base px-6 sm:px-8 py-3 sm:py-4 min-h-[44px] sm:min-h-[52px] font-medium w-full sm:w-auto flex-1 sm:flex-initial"
            >
              {{ $t('hero.ctaSecondary') }}
            </a>
          </div>
        </div>
      </div>
    </section>

    <!-- Stats Section -->
    <section class="py-20 md:py-28 bg-[#050505]">
      <div class="container mx-auto px-4 md:px-6 lg:px-8">
        <div class="max-w-4xl mx-auto">
          <div class="grid grid-cols-1 md:grid-cols-3 gap-12 md:gap-16">
            <div class="text-center animate-fadeInUp" style="animation-delay: 0.1s;">
              <div class="text-3xl md:text-4xl font-bold text-[#f9f9f9] mb-3">1000+</div>
              <div class="text-base text-[#8b949e] font-medium">{{ $t('hero.stats.prospects') }}</div>
            </div>
            <div class="text-center animate-fadeInUp" style="animation-delay: 0.2s;">
              <div class="text-3xl md:text-4xl font-bold text-[#f9f9f9] mb-3">50+</div>
              <div class="text-base text-[#8b949e] font-medium">{{ $t('hero.stats.developers') }}</div>
            </div>
            <div class="text-center animate-fadeInUp" style="animation-delay: 0.3s;">
              <div class="text-3xl md:text-4xl font-bold text-[#f9f9f9] mb-3">95%</div>
              <div class="text-base text-[#8b949e] font-medium">{{ $t('hero.stats.satisfaction') }}</div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Main Features Section -->
    <section id="features" class="py-32 md:py-40 bg-[#050505]">
      <div class="container mx-auto px-4 md:px-6 lg:px-8">
        <div class="max-w-7xl mx-auto space-y-32">
          <!-- Feature 1: Recherche -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-16 md:gap-20 items-center">
            <div class="animate-slideInLeft">
              <div class="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#1a1a1a]/50 border border-[#30363d]/30 mb-8">
                <i class="fa-solid fa-search text-[#8b949e] text-sm"></i>
                <span class="text-sm font-medium text-[#8b949e]">{{ $t('features.search.badge') }}</span>
              </div>
              <h2 class="text-xl md:text-2xl lg:text-3xl font-bold text-[#f9f9f9] mb-6 tracking-tight">
                {{ $t('features.search.heading') }}
              </h2>
              <p class="text-sm text-[#8b949e] mb-8 leading-relaxed font-light">
                {{ $t('features.search.descriptionFull') }}
              </p>
              <ul class="space-y-4">
                <li class="flex items-start gap-3">
                  <i class="fa-solid fa-check text-[#2BAD5F] mt-1 text-base"></i>
                  <span class="text-base text-[#8b949e] font-light">{{ $t('features.search.feature1') }}</span>
                </li>
                <li class="flex items-start gap-3">
                  <i class="fa-solid fa-check text-[#2BAD5F] mt-1 text-base"></i>
                  <span class="text-base text-[#8b949e] font-light">{{ $t('features.search.feature2') }}</span>
                </li>
                <li class="flex items-start gap-3">
                  <i class="fa-solid fa-check text-[#2BAD5F] mt-1 text-base"></i>
                  <span class="text-base text-[#8b949e] font-light">{{ $t('features.search.feature3') }}</span>
                </li>
                <li class="flex items-start gap-3">
                  <i class="fa-solid fa-check text-[#2BAD5F] mt-1 text-base"></i>
                  <span class="text-base text-[#8b949e] font-light">{{ $t('features.search.feature4') }}</span>
                </li>
              </ul>
            </div>
            <div class="bg-[#1a1a1a] rounded-xl border border-[#30363d] p-3 md:p-6 animate-slideInRight">
              <div class="space-y-4">
                <div class="flex items-center gap-4 p-4 bg-[#050505] rounded-lg border border-[#30363d] hover:border-[#30363d]/70 transition-colors">
                  <i class="fa-solid fa-building text-[#8b949e] text-lg"></i>
                  <div>
                    <div class="text-base font-medium text-[#f9f9f9]">Restaurant Le Gourmet</div>
                    <div class="text-sm text-[#8b949e] font-light">Paris, 75001</div>
                  </div>
                </div>
                <div class="flex items-center gap-4 p-4 bg-[#050505] rounded-lg border border-[#30363d] hover:border-[#30363d]/70 transition-colors">
                  <i class="fa-solid fa-building text-[#8b949e] text-lg"></i>
                  <div>
                    <div class="text-base font-medium text-[#f9f9f9]">Salon de coiffure Style</div>
                    <div class="text-sm text-[#8b949e] font-light">Lyon, 69001</div>
                  </div>
                </div>
                <div class="flex items-center gap-4 p-4 bg-[#050505] rounded-lg border border-[#30363d] hover:border-[#30363d]/70 transition-colors">
                  <i class="fa-solid fa-building text-[#8b949e] text-lg"></i>
                  <div>
                    <div class="text-base font-medium text-[#f9f9f9]">Cabinet médical Santé</div>
                    <div class="text-sm text-[#8b949e] font-light">Marseille, 13001</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Feature 2: Campagnes -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-16 md:gap-20 items-center">
            <div class="order-2 md:order-1 animate-slideInRight">
              <div class="bg-[#1a1a1a] rounded-xl border border-[#30363d] p-3 md:p-6">
                <div class="space-y-4">
                  <div class="p-6 bg-[#050505] rounded-lg border border-[#30363d] hover:border-[#30363d]/70 transition-colors">
                    <div class="text-base font-semibold text-[#f9f9f9] mb-3">{{ $t('features.campaigns.campaignExample') }}</div>
                    <div class="flex flex-col md:flex-row items-start md:items-center gap-3 md:gap-6 text-sm text-[#8b949e] font-light">
                      <span><i class="fa-solid fa-users mr-2"></i> 25 {{ $t('features.campaigns.prospects') }}</span>
                      <span><i class="fa-solid fa-envelope mr-2"></i> 20 {{ $t('features.campaigns.sent') }}</span>
                      <span><i class="fa-solid fa-check mr-2"></i> 5 {{ $t('features.campaigns.replies') }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div class="order-1 md:order-2 animate-slideInLeft">
              <div class="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#1a1a1a]/50 border border-[#30363d]/30 mb-8">
                <i class="fa-solid fa-envelope text-[#8b949e] text-sm"></i>
                <span class="text-sm font-medium text-[#8b949e]">{{ $t('features.campaigns.badge') }}</span>
              </div>
              <h2 class="text-xl md:text-2xl lg:text-3xl font-bold text-[#f9f9f9] mb-6 tracking-tight">
                {{ $t('features.campaigns.heading') }}
              </h2>
              <p class="text-sm text-[#8b949e] mb-8 leading-relaxed font-light">
                {{ $t('features.campaigns.descriptionFull') }}
              </p>
              <ul class="space-y-4">
                <li class="flex items-start gap-3">
                  <i class="fa-solid fa-check text-[#2BAD5F] mt-1 text-base"></i>
                  <span class="text-base text-[#8b949e] font-light">{{ $t('features.campaigns.feature1') }}</span>
                </li>
                <li class="flex items-start gap-3">
                  <i class="fa-solid fa-check text-[#2BAD5F] mt-1 text-base"></i>
                  <span class="text-base text-[#8b949e] font-light">{{ $t('features.campaigns.feature2') }}</span>
                </li>
                <li class="flex items-start gap-3">
                  <i class="fa-solid fa-check text-[#2BAD5F] mt-1 text-base"></i>
                  <span class="text-base text-[#8b949e] font-light">{{ $t('features.campaigns.feature3') }}</span>
                </li>
                <li class="flex items-start gap-3">
                  <i class="fa-solid fa-check text-[#2BAD5F] mt-1 text-base"></i>
                  <span class="text-base text-[#8b949e] font-light">{{ $t('features.campaigns.feature4') }}</span>
                </li>
              </ul>
            </div>
          </div>

          <!-- Feature 3: Gestion -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-16 md:gap-20 items-center">
            <div class="animate-slideInLeft">
              <div class="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#1a1a1a]/50 border border-[#30363d]/30 mb-8">
                <i class="fa-solid fa-database text-[#8b949e] text-sm"></i>
                <span class="text-sm font-medium text-[#8b949e]">{{ $t('features.management.badge') }}</span>
              </div>
              <h2 class="text-xl md:text-2xl lg:text-3xl font-bold text-[#f9f9f9] mb-6 tracking-tight">
                {{ $t('features.management.heading') }}
              </h2>
              <p class="text-sm text-[#8b949e] mb-8 leading-relaxed font-light">
                {{ $t('features.management.descriptionFull') }}
              </p>
              <ul class="space-y-4">
                <li class="flex items-start gap-3">
                  <i class="fa-solid fa-check text-[#2BAD5F] mt-1 text-base"></i>
                  <span class="text-base text-[#8b949e] font-light">{{ $t('features.management.feature1') }}</span>
                </li>
                <li class="flex items-start gap-3">
                  <i class="fa-solid fa-check text-[#2BAD5F] mt-1 text-base"></i>
                  <span class="text-base text-[#8b949e] font-light">{{ $t('features.management.feature2') }}</span>
                </li>
                <li class="flex items-start gap-3">
                  <i class="fa-solid fa-check text-[#2BAD5F] mt-1 text-base"></i>
                  <span class="text-base text-[#8b949e] font-light">{{ $t('features.management.feature3') }}</span>
                </li>
                <li class="flex items-start gap-3">
                  <i class="fa-solid fa-check text-[#2BAD5F] mt-1 text-base"></i>
                  <span class="text-base text-[#8b949e] font-light">{{ $t('features.management.feature4') }}</span>
                </li>
              </ul>
            </div>
            <div class="bg-[#1a1a1a] rounded-xl border border-[#30363d] p-3 md:p-6 animate-slideInRight">
              <div class="space-y-4">
                <div class="p-6 bg-[#050505] rounded-lg border border-[#30363d] hover:border-[#30363d]/70 transition-colors">
                  <div class="flex items-center justify-between mb-3">
                    <div class="text-base font-semibold text-[#f9f9f9]">{{ $t('features.management.myProspects') }}</div>
                    <span class="text-sm text-[#2BAD5F] bg-[#2BAD5F]/10 px-3 py-1 rounded-lg font-medium">125</span>
                  </div>
                  <div class="text-sm text-[#8b949e] font-light">{{ $t('features.management.allContacts') }}</div>
                </div>
                <div class="p-6 bg-[#050505] rounded-lg border border-[#30363d] hover:border-[#30363d]/70 transition-colors">
                  <div class="flex items-center justify-between mb-3">
                    <div class="text-base font-semibold text-[#f9f9f9]">{{ $t('features.management.activeCampaigns') }}</div>
                    <span class="text-sm text-[#8b949e] bg-[#30363d]/50 px-3 py-1 rounded-lg font-medium">3</span>
                  </div>
                  <div class="text-sm text-[#8b949e] font-light">{{ $t('features.management.trackCampaigns') }}</div>
                </div>
              </div>
            </div>
          </div>

          <!-- Feature 4: Statistiques -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-16 md:gap-20 items-center">
            <div class="order-2 md:order-1 animate-slideInRight">
              <div class="bg-[#1a1a1a] rounded-xl border border-[#30363d] p-3 md:p-6">
                <div class="space-y-4">
                  <div class="p-6 bg-[#050505] rounded-lg border border-[#30363d] hover:border-[#30363d]/70 transition-colors">
                    <div class="text-sm text-[#8b949e] mb-2 font-medium">{{ $t('features.analytics.openRate') }}</div>
                    <div class="text-2xl font-bold text-[#f9f9f9]">68%</div>
                  </div>
                  <div class="p-6 bg-[#050505] rounded-lg border border-[#30363d] hover:border-[#30363d]/70 transition-colors">
                    <div class="text-sm text-[#8b949e] mb-2 font-medium">{{ $t('features.analytics.replyRate') }}</div>
                    <div class="text-2xl font-bold text-[#f9f9f9]">24%</div>
                  </div>
                  <div class="p-6 bg-[#050505] rounded-lg border border-[#30363d] hover:border-[#30363d]/70 transition-colors">
                    <div class="text-sm text-[#8b949e] mb-2 font-medium">{{ $t('features.analytics.converted') }}</div>
                    <div class="text-2xl font-bold text-[#2BAD5F]">12</div>
                  </div>
                </div>
              </div>
            </div>
            <div class="order-1 md:order-2 animate-slideInLeft">
              <div class="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#1a1a1a]/50 border border-[#30363d]/30 mb-8">
                <i class="fa-solid fa-chart-line text-[#8b949e] text-sm"></i>
                <span class="text-sm font-medium text-[#8b949e]">{{ $t('features.analytics.badge') }}</span>
              </div>
              <h2 class="text-xl md:text-2xl lg:text-3xl font-bold text-[#f9f9f9] mb-6 tracking-tight">
                {{ $t('features.analytics.heading') }}
              </h2>
              <p class="text-sm text-[#8b949e] mb-8 leading-relaxed font-light">
                {{ $t('features.analytics.descriptionFull') }}
              </p>
              <ul class="space-y-4">
                <li class="flex items-start gap-3">
                  <i class="fa-solid fa-check text-[#2BAD5F] mt-1 text-base"></i>
                  <span class="text-base text-[#8b949e] font-light">{{ $t('features.analytics.feature1') }}</span>
                </li>
                <li class="flex items-start gap-3">
                  <i class="fa-solid fa-check text-[#2BAD5F] mt-1 text-base"></i>
                  <span class="text-base text-[#8b949e] font-light">{{ $t('features.analytics.feature2') }}</span>
                </li>
                <li class="flex items-start gap-3">
                  <i class="fa-solid fa-check text-[#2BAD5F] mt-1 text-base"></i>
                  <span class="text-base text-[#8b949e] font-light">{{ $t('features.analytics.feature3') }}</span>
                </li>
                <li class="flex items-start gap-3">
                  <i class="fa-solid fa-check text-[#2BAD5F] mt-1 text-base"></i>
                  <span class="text-base text-[#8b949e] font-light">{{ $t('features.analytics.feature4') }}</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Pricing Section -->
    <section id="pricing" class="py-32 md:py-40 bg-[#050505]">
      <div class="container mx-auto px-4 md:px-6 lg:px-8">
        <div class="text-center mb-20">
          <h2 class="text-2xl md:text-3xl lg:text-4xl font-bold text-[#f9f9f9] mb-5 tracking-tight">
            {{ $t('pricing.title') }}
          </h2>
          <p class="text-base md:text-lg text-[#8b949e] max-w-2xl mx-auto font-light">
            {{ $t('pricing.subtitle') }}
          </p>
        </div>

        <div v-if="isLoading" class="max-w-4xl mx-auto">
          <div class="bg-[#1a1a1a] rounded-lg border border-[#30363d]/50 p-8 animate-pulse">
            <div class="h-6 bg-[#21262d] rounded w-1/3 mb-4"></div>
            <div class="h-4 bg-[#21262d] rounded w-2/3 mb-6"></div>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div class="h-20 bg-[#21262d] rounded"></div>
              <div class="h-20 bg-[#21262d] rounded"></div>
              <div class="h-20 bg-[#21262d] rounded"></div>
              <div class="h-20 bg-[#21262d] rounded"></div>
            </div>
          </div>
        </div>

        <div v-else-if="creditSettings" class="max-w-5xl mx-auto">
          <!-- Credit Info Card -->
          <div class="bg-transparent rounded-2xl border border-[#30363d]/30 p-4 md:p-12">
            <h3 class="text-xl md:text-2xl font-bold text-[#f9f9f9] mb-4">{{ $t('pricing.creditsTitle') }}</h3>
            <p class="text-sm text-[#8b949e] mb-10 font-light">{{ $t('pricing.creditsSubtitle') }}</p>
            
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-10">
              <div class="bg-transparent rounded-xl border border-[#30363d]/30 p-6 hover:border-[#30363d]/50 transition-all">
                <div class="w-12 h-12 rounded-xl bg-[#21262d]/50 flex items-center justify-center mb-4">
                  <i class="fa-solid fa-search text-[#f9f9f9] text-lg"></i>
                </div>
                <h4 class="text-lg font-semibold text-[#f9f9f9] mb-2">{{ $t('pricing.search.title') }}</h4>
                <p class="text-base text-[#8b949e] font-light">{{ $t('pricing.search.description') }}</p>
              </div>
              <div class="bg-transparent rounded-xl border border-[#30363d]/30 p-6 hover:border-[#30363d]/50 transition-all">
                <div class="w-12 h-12 rounded-xl bg-[#21262d]/50 flex items-center justify-center mb-4">
                  <i class="fa-solid fa-envelope text-[#f9f9f9] text-lg"></i>
                </div>
                <h4 class="text-lg font-semibold text-[#f9f9f9] mb-2">{{ $t('pricing.email.title') }}</h4>
                <p class="text-base text-[#8b949e] font-light">{{ $t('pricing.email.description') }}</p>
              </div>
            </div>

            <!-- Credit Pricing Details -->
            <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-6 pt-10 border-t border-[#30363d]/30">
              <div class="text-center">
                <div class="text-sm text-[#8b949e] mb-2 font-medium">{{ $t('pricing.pricePerCredit') }}</div>
                <div class="text-xl font-bold text-[#f9f9f9]">€{{ creditSettings.price_per_credit.toFixed(2) }}</div>
              </div>
              <div class="text-center">
                <div class="text-sm text-[#8b949e] mb-2 font-medium">{{ $t('pricing.creditsPerSearch') }}</div>
                <div class="text-xl font-bold text-[#f9f9f9]">{{ creditSettings.credits_per_search }}</div>
              </div>
              <div class="text-center">
                <div class="text-sm text-[#8b949e] mb-2 font-medium">{{ $t('pricing.creditsPerResult') }}</div>
                <div class="text-xl font-bold text-[#f9f9f9]">{{ creditSettings.credits_per_result }}</div>
              </div>
              <div class="text-center">
                <div class="text-sm text-[#8b949e] mb-2 font-medium">{{ $t('pricing.creditsPerEmail') }}</div>
                <div class="text-xl font-bold text-[#f9f9f9]">{{ creditSettings.credits_per_email }}</div>
              </div>
            </div>

            <!-- Free Credits & Minimum -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mt-10 pt-10 border-t border-[#30363d]/30">
              <div class="bg-transparent rounded-xl border border-[#30363d]/30 p-6">
                <div class="text-sm text-[#8b949e] mb-2 font-medium">{{ $t('pricing.freeCredits') }}</div>
                <div class="text-2xl font-bold text-[#2BAD5F]">{{ creditSettings.free_credits_on_signup }}</div>
              </div>
              <div class="bg-transparent rounded-xl border border-[#30363d]/30 p-6">
                <div class="text-sm text-[#8b949e] mb-2 font-medium">{{ $t('pricing.minPurchase') }}</div>
                <div class="text-2xl font-bold text-[#f9f9f9]">{{ creditSettings.minimum_credits_purchase }}</div>
              </div>
            </div>
          </div>
        </div>

        <div v-else class="max-w-4xl mx-auto">
          <div class="bg-[#1a1a1a] rounded-lg border border-[#30363d]/50 p-8 text-center">
            <p class="text-[#8b949e]">Failed to load credit settings. Please try again later.</p>
          </div>
        </div>
      </div>
    </section>

    <!-- How It Works Section -->
    <section class="py-32 md:py-40 bg-[#1a1a1a]">
      <div class="container mx-auto px-4 md:px-6 lg:px-8">
        <div class="text-center mb-20">
          <h2 class="text-2xl md:text-3xl lg:text-4xl font-bold text-[#f9f9f9] mb-5 tracking-tight">
            {{ $t('howItWorks.title') }}
          </h2>
          <p class="text-sm md:text-base text-[#8b949e] max-w-2xl mx-auto font-light">
            {{ $t('howItWorks.subtitle') }}
          </p>
        </div>

        <div class="max-w-5xl mx-auto px-2 md:px-0">
          <div class="space-y-20">
            <!-- Step 1 -->
            <div class="flex flex-col md:flex-row gap-10 items-start animate-fadeInUp" style="animation-delay: 0.1s;">
              <div class="flex-shrink-0 w-16 h-16 rounded-2xl bg-[#21262d]/50 flex items-center justify-center text-[#f9f9f9] text-2xl font-bold">
                1
              </div>
              <div class="flex-1">
                <h3 class="text-lg md:text-xl font-semibold text-[#f9f9f9] mb-4">{{ $t('howItWorks.step1.title') }}</h3>
                <p class="text-sm text-[#8b949e] leading-relaxed font-light">
                  {{ $t('howItWorks.step1.description') }}
                </p>
              </div>
            </div>

            <!-- Step 2 -->
            <div class="flex flex-col md:flex-row gap-10 items-start animate-fadeInUp" style="animation-delay: 0.2s;">
              <div class="flex-shrink-0 w-16 h-16 rounded-2xl bg-[#21262d]/50 flex items-center justify-center text-[#f9f9f9] text-2xl font-bold">
                2
              </div>
              <div class="flex-1">
                <h3 class="text-lg md:text-xl font-semibold text-[#f9f9f9] mb-4">{{ $t('howItWorks.step2.title') }}</h3>
                <p class="text-sm text-[#8b949e] leading-relaxed font-light">
                  {{ $t('howItWorks.step2.description') }}
                </p>
              </div>
            </div>

            <!-- Step 3 -->
            <div class="flex flex-col md:flex-row gap-10 items-start animate-fadeInUp" style="animation-delay: 0.3s;">
              <div class="flex-shrink-0 w-16 h-16 rounded-2xl bg-[#21262d]/50 flex items-center justify-center text-[#f9f9f9] text-2xl font-bold">
                3
              </div>
              <div class="flex-1">
                <h3 class="text-lg md:text-xl font-semibold text-[#f9f9f9] mb-4">{{ $t('howItWorks.step3.title') }}</h3>
                <p class="text-sm text-[#8b949e] leading-relaxed font-light">
                  {{ $t('howItWorks.step3.description') }}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Additional Features Grid -->
    <section class="py-32 md:py-40 bg-[#050505]">
      <div class="container mx-auto px-4 md:px-6 lg:px-8">
        <div class="text-center mb-20">
          <h2 class="text-xl md:text-2xl lg:text-3xl font-bold text-[#f9f9f9] mb-5 tracking-tight">
            {{ $t('features.more.title') }}
          </h2>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-10 max-w-7xl mx-auto">
          <div class="bg-[#1a1a1a] rounded-xl border border-[#30363d] p-4 md:p-8 hover:border-[#30363d]/70 hover:scale-105 transition-all duration-300 animate-fadeInUp" style="animation-delay: 0.1s;">
            <i class="fa-solid fa-coins text-xl text-[#8b949e] mb-4"></i>
            <h3 class="text-base font-semibold text-[#f9f9f9] mb-3">{{ $t('features.more.credits.title') }}</h3>
            <p class="text-sm text-[#8b949e] font-light leading-relaxed">{{ $t('features.more.credits.description') }}</p>
          </div>
          <div class="bg-[#1a1a1a] rounded-xl border border-[#30363d] p-4 md:p-8 hover:border-[#30363d]/70 hover:scale-105 transition-all duration-300 animate-fadeInUp" style="animation-delay: 0.2s;">
            <i class="fa-solid fa-envelope-circle-check text-xl text-[#8b949e] mb-4"></i>
            <h3 class="text-base font-semibold text-[#f9f9f9] mb-3">{{ $t('features.more.emailAccounts.title') }}</h3>
            <p class="text-sm text-[#8b949e] font-light leading-relaxed">{{ $t('features.more.emailAccounts.description') }}</p>
          </div>
          <div class="bg-[#1a1a1a] rounded-xl border border-[#30363d] p-4 md:p-8 hover:border-[#30363d]/70 hover:scale-105 transition-all duration-300 animate-fadeInUp" style="animation-delay: 0.3s;">
            <i class="fa-solid fa-file-lines text-xl text-[#8b949e] mb-4"></i>
            <h3 class="text-base font-semibold text-[#f9f9f9] mb-3">{{ $t('features.more.templates.title') }}</h3>
            <p class="text-sm text-[#8b949e] font-light leading-relaxed">{{ $t('features.more.templates.description') }}</p>
          </div>
          <div class="bg-[#1a1a1a] rounded-xl border border-[#30363d] p-4 md:p-8 hover:border-[#30363d]/70 hover:scale-105 transition-all duration-300 animate-fadeInUp" style="animation-delay: 0.4s;">
            <i class="fa-solid fa-headset text-xl text-[#8b949e] mb-4"></i>
            <h3 class="text-base font-semibold text-[#f9f9f9] mb-3">{{ $t('features.more.support.title') }}</h3>
            <p class="text-sm text-[#8b949e] font-light leading-relaxed">{{ $t('features.more.support.description') }}</p>
          </div>
          <div class="bg-[#1a1a1a] rounded-xl border border-[#30363d] p-4 md:p-8 hover:border-[#30363d]/70 hover:scale-105 transition-all duration-300 animate-fadeInUp" style="animation-delay: 0.5s;">
            <i class="fa-solid fa-mobile-screen text-xl text-[#8b949e] mb-4"></i>
            <h3 class="text-base font-semibold text-[#f9f9f9] mb-3">{{ $t('features.more.responsive.title') }}</h3>
            <p class="text-sm text-[#8b949e] font-light leading-relaxed">{{ $t('features.more.responsive.description') }}</p>
          </div>
          <div class="bg-[#1a1a1a] rounded-xl border border-[#30363d] p-4 md:p-8 hover:border-[#30363d]/70 hover:scale-105 transition-all duration-300 animate-fadeInUp" style="animation-delay: 0.6s;">
            <i class="fa-solid fa-lock text-xl text-[#8b949e] mb-4"></i>
            <h3 class="text-base font-semibold text-[#f9f9f9] mb-3">{{ $t('features.more.security.title') }}</h3>
            <p class="text-sm text-[#8b949e] font-light leading-relaxed">{{ $t('features.more.security.description') }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- FAQ Section -->
    <section class="py-32 md:py-40 bg-[#050505]">
      <div class="container mx-auto px-4 md:px-6 lg:px-8">
        <div class="max-w-4xl mx-auto">
          <div class="text-center mb-20">
            <h2 class="text-2xl md:text-3xl font-bold text-[#f9f9f9] mb-5">
              {{ $t('pricing.faq.title') }}
            </h2>
          </div>
          <div class="space-y-4">
            <div 
              v-for="(faq, index) in faqs" 
              :key="index"
              class="bg-[#1a1a1a] rounded-lg border border-[#30363d] overflow-hidden"
            >
              <button
                @click="toggleFaq(index)"
                class="w-full flex items-center justify-between p-6 text-left hover:bg-[#21262d] transition-colors"
              >
                <h3 class="text-lg font-semibold text-[#f9f9f9] pr-4">
                  {{ faq.question }}
                </h3>
                <i 
                  :class="[
                    'fa-solid transition-transform flex-shrink-0',
                    openFaqs.has(index) ? 'fa-chevron-up' : 'fa-chevron-down',
                    openFaqs.has(index) ? 'text-[#f9f9f9]' : 'text-[#8b949e]'
                  ]"
                ></i>
              </button>
              <div 
                v-show="openFaqs.has(index)"
                class="px-6 pb-6"
              >
                <p class="text-base text-[#8b949e] font-light leading-relaxed">
                  {{ faq.answer }}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- CTA Section -->
    <section class="py-32 md:py-40 bg-[#050505]">
      <div class="container mx-auto px-4 md:px-6 lg:px-8">
        <div class="max-w-4xl mx-auto text-center">
          <h2 class="text-2xl md:text-3xl lg:text-4xl font-bold text-[#f9f9f9] mb-6 tracking-tight">
            {{ $t('cta.title') }}
          </h2>
          <p class="text-base md:text-lg text-[#8b949e] mb-10 max-w-2xl mx-auto leading-relaxed font-light">
            {{ $t('cta.subtitle') }}
          </p>
          <div class="flex flex-col sm:flex-row gap-4 justify-center">
            <NuxtLink 
              :to="localePath('/signup')" 
              class="btn-primary text-sm sm:text-base px-6 sm:px-8 py-3 sm:py-4 min-h-[44px] sm:min-h-[52px] font-medium w-full sm:w-auto flex-1 sm:flex-initial"
            >
              {{ $t('cta.primary') }}
            </NuxtLink>
            <a 
              href="#pricing" 
              @click.prevent="scrollToSection('#pricing')"
              class="btn-secondary text-sm sm:text-base px-6 sm:px-8 py-3 sm:py-4 min-h-[44px] sm:min-h-[52px] font-medium w-full sm:w-auto flex-1 sm:flex-initial"
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
import type { CreditSettings } from '~/types';
import type { Ref } from 'vue';
import { ref, onMounted } from 'vue';
import * as creditSettingsService from '~/services/creditSettingsService';

/**
 * Landing page - Marketing page with hero, features, pricing, and CTA sections
 */
definePageMeta({
  layout: 'marketing'
});

const localePath = useLocalePath();
const { t } = useI18n();

/**
 * Credit settings state
 */
const creditSettings: Ref<CreditSettings | null> = ref(null);
const isLoading: Ref<boolean> = ref(true);

/**
 * FAQ state
 */
const openFaqs: Ref<Set<number>> = ref(new Set([0])); // First FAQ open by default

/**
 * FAQ data
 */
const faqs = computed(() => [
  {
    question: t('pricing.faq.q1'),
    answer: t('pricing.faq.a1')
  },
  {
    question: t('pricing.faq.q2'),
    answer: t('pricing.faq.a2')
  },
  {
    question: t('pricing.faq.q3'),
    answer: t('pricing.faq.a3')
  }
]);

/**
 * Toggle FAQ
 */
const toggleFaq = (index: number): void => {
  if (openFaqs.value.has(index)) {
    openFaqs.value.delete(index);
  } else {
    openFaqs.value.add(index);
  }
};

/**
 * Load credit settings from API
 */
const loadCreditSettings = async (): Promise<void> => {
  try {
    isLoading.value = true;
    creditSettings.value = await creditSettingsService.getCreditSettings();
  } catch (error) {
    console.error('Failed to load credit settings:', error);
  } finally {
    isLoading.value = false;
  }
};

/**
 * Smooth scroll to section
 */
const scrollToSection = (selector: string): void => {
  const element = document.querySelector(selector);
  if (element) {
    const headerOffset = 80;
    const elementPosition = element.getBoundingClientRect().top;
    const offsetPosition = elementPosition + window.pageYOffset - headerOffset;

    window.scrollTo({
      top: offsetPosition,
      behavior: 'smooth'
    });
  }
};

/**
 * Initialize
 */
onMounted(async () => {
  await loadCreditSettings();
});

// SEO Meta
useHead({
  title: () => t('hero.title') + ' ' + t('hero.titleHighlight') + ' - devleadhunter',
  meta: [
    {
      name: 'description',
      content: () => t('hero.subtitle')
    }
  ]
});
</script>
