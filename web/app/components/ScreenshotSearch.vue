<template>
  <div class="overflow-hidden rounded-xl border border-[#30363d]/30 bg-[#050505] shadow-2xl">
    <!-- Browser Chrome -->
    <div class="flex items-center gap-2 border-b border-[#30363d]/30 bg-[#1a1a1a] px-4 py-3">
      <div class="flex gap-1.5">
        <div class="h-3 w-3 rounded-full bg-[#DC4747]"></div>
        <div class="h-3 w-3 rounded-full bg-[#f9f9f9]/20"></div>
        <div class="h-3 w-3 rounded-full bg-[#2BAD5F]"></div>
      </div>
      <div class="flex-1 rounded-lg bg-[#050505] px-4 py-1.5 text-center text-xs font-light text-[#8b949e]">
        devleadhunter.dibodev.fr/dashboard/search-prospects
      </div>
    </div>

    <!-- App Content -->
    <div class="flex h-[500px]">
      <!-- Sidebar -->
      <div class="w-64 border-r border-[#30363d]/30 bg-[#1a1a1a] p-6">
        <div class="mb-8 flex items-center gap-2.5">
          <div class="flex h-5 w-5 items-center justify-center">
            <svg
              class="h-full w-full fill-current text-[#f9f9f9]"
              viewBox="0 0 493 515"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M40.6667 1.73334C13.3333 8.80001 2.93333 27.6 8.53333 59.3333C9.73333 65.8667 15.4667 86.6667 21.3333 105.333C33.4667 143.6 41.2 173.733 45.6 199.333C48 213.867 48.5333 221.867 48.5333 248C48.6667 296.8 44.1333 319.067 19.3333 392.667C3.46667 440 0 453.867 0 469.867C0 489.067 6.8 500.933 21.7333 508.133C44.2667 518.8 77.8667 516.133 107.333 501.333C144.533 482.667 158.933 460.133 168.667 404.933C174.8 369.6 179.733 357.6 194 343.2C199.2 337.867 207.6 331.333 212.933 328.133C233.067 316.533 266.267 305.733 291.467 302.667C298 301.867 305.333 301.067 307.733 300.667L312 300.133V335.067C312 385.6 314.667 410.933 322.267 435.2C333.333 470.533 356.267 493.333 393.867 506.533C435.067 521.067 476 515.067 486.533 492.933C493.6 477.867 491.467 464.133 473.867 410.933C459.867 368.8 452.533 341.733 447.867 315.333C445.2 300.533 444.8 293.6 444.8 267.333C444.8 241.6 445.333 234 447.867 220C453.333 189.2 460 164.4 477.6 108C491.867 62.1333 494.533 45.2 490 29.7333C484.267 10.4 465.6 5.71296e-06 437.067 5.71296e-06C405.867 5.71296e-06 378.533 10.8 358.4 31.0667C341.467 47.8667 331.6 71.3333 325.467 108.667C321.2 134.533 317.733 147.467 312.4 158.667C298 188.8 258.533 207.6 192.933 215.467C182.8 216.667 174.267 217.333 173.867 216.933C173.467 216.533 173.867 206.133 174.8 193.867C178.667 139.867 172.133 78 160.133 53.0667C148.8 29.4667 126 12.1333 96.1333 4.40001C80.5333 0.400006 51.4667 -1.06666 40.6667 1.73334Z"
                fill="currentColor"
              />
            </svg>
          </div>
          <span class="text-sm font-semibold text-[#f9f9f9]">devleadhunter</span>
        </div>
      </div>

      <!-- Main Content -->
      <div class="flex-1 overflow-y-auto bg-[#050505] p-8">
        <h1 class="mb-3 text-3xl font-bold text-[#f9f9f9]">Recherche en cours</h1>
        <p class="mb-8 text-sm font-light text-[#8b949e]">Recherche de prospects en cours...</p>

        <div class="space-y-6 rounded-xl border border-[#30363d]/30 bg-transparent p-8">
          <div class="flex items-center justify-between">
            <div class="flex-1">
              <div class="mb-4 flex items-center gap-3">
                <div class="h-2.5 w-2.5 animate-pulse rounded-full bg-[#2BAD5F]"></div>
                <span class="text-base font-medium text-[#f9f9f9]">Recherche active</span>
              </div>
              <div class="mb-3 h-2.5 overflow-hidden rounded-full bg-[#050505]">
                <div class="h-full rounded-full bg-[#2BAD5F] transition-all" style="width: 65%"></div>
              </div>
              <p class="text-sm font-light text-[#8b949e]">65% complété - 13 prospects trouvés</p>
            </div>
          </div>

          <div class="space-y-3 border-t border-[#30363d]/30 pt-6">
            <div class="flex items-center gap-4 rounded-xl border border-[#30363d]/30 bg-[#050505] p-4">
              <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-[#21262d]/50">
                <i class="fa-solid fa-building text-base text-[#8b949e]"></i>
              </div>
              <div class="flex-1">
                <div class="text-base font-medium text-[#f9f9f9]">Restaurant Le Gourmet</div>
                <div class="text-sm font-light text-[#8b949e]">Paris, 75001</div>
              </div>
              <div class="rounded-lg bg-[#2BAD5F]/10 px-3 py-1.5 text-sm font-medium text-[#2BAD5F]">Confiance: 3</div>
            </div>
            <div class="flex items-center gap-4 rounded-xl border border-[#30363d]/30 bg-[#050505] p-4">
              <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-[#21262d]/50">
                <i class="fa-solid fa-building text-base text-[#8b949e]"></i>
              </div>
              <div class="flex-1">
                <div class="text-base font-medium text-[#f9f9f9]">Salon de coiffure Style</div>
                <div class="text-sm font-light text-[#8b949e]">Lyon, 69001</div>
              </div>
              <div class="rounded-lg bg-[#2BAD5F]/10 px-3 py-1.5 text-sm font-medium text-[#2BAD5F]">Confiance: 4</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * Screenshot component for Search Prospects view
 */
</script>
