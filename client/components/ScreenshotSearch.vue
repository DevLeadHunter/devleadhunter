<template>
  <div class="bg-[#050505] rounded-xl border border-[#30363d]/30 overflow-hidden shadow-2xl">
    <!-- Browser Chrome -->
    <div class="bg-[#1a1a1a] border-b border-[#30363d]/30 px-4 py-3 flex items-center gap-2">
      <div class="flex gap-1.5">
        <div class="w-3 h-3 rounded-full bg-[#DC4747]"></div>
        <div class="w-3 h-3 rounded-full bg-[#f9f9f9]/20"></div>
        <div class="w-3 h-3 rounded-full bg-[#2BAD5F]"></div>
      </div>
      <div class="flex-1 bg-[#050505] rounded-lg px-4 py-1.5 text-xs text-[#8b949e] text-center font-light">
        devleadhunter.dibodev.fr/dashboard/search-prospects
      </div>
    </div>
    
    <!-- App Content -->
    <div class="flex h-[500px]">
      <!-- Sidebar -->
      <div class="w-64 bg-[#1a1a1a] border-r border-[#30363d]/30 p-6">
        <div class="flex items-center gap-2.5 mb-8">
          <div class="w-5 h-5 flex items-center justify-center">
            <svg class="w-full h-full fill-current text-[#f9f9f9]" viewBox="0 0 493 515" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M40.6667 1.73334C13.3333 8.80001 2.93333 27.6 8.53333 59.3333C9.73333 65.8667 15.4667 86.6667 21.3333 105.333C33.4667 143.6 41.2 173.733 45.6 199.333C48 213.867 48.5333 221.867 48.5333 248C48.6667 296.8 44.1333 319.067 19.3333 392.667C3.46667 440 0 453.867 0 469.867C0 489.067 6.8 500.933 21.7333 508.133C44.2667 518.8 77.8667 516.133 107.333 501.333C144.533 482.667 158.933 460.133 168.667 404.933C174.8 369.6 179.733 357.6 194 343.2C199.2 337.867 207.6 331.333 212.933 328.133C233.067 316.533 266.267 305.733 291.467 302.667C298 301.867 305.333 301.067 307.733 300.667L312 300.133V335.067C312 385.6 314.667 410.933 322.267 435.2C333.333 470.533 356.267 493.333 393.867 506.533C435.067 521.067 476 515.067 486.533 492.933C493.6 477.867 491.467 464.133 473.867 410.933C459.867 368.8 452.533 341.733 447.867 315.333C445.2 300.533 444.8 293.6 444.8 267.333C444.8 241.6 445.333 234 447.867 220C453.333 189.2 460 164.4 477.6 108C491.867 62.1333 494.533 45.2 490 29.7333C484.267 10.4 465.6 5.71296e-06 437.067 5.71296e-06C405.867 5.71296e-06 378.533 10.8 358.4 31.0667C341.467 47.8667 331.6 71.3333 325.467 108.667C321.2 134.533 317.733 147.467 312.4 158.667C298 188.8 258.533 207.6 192.933 215.467C182.8 216.667 174.267 217.333 173.867 216.933C173.467 216.533 173.867 206.133 174.8 193.867C178.667 139.867 172.133 78 160.133 53.0667C148.8 29.4667 126 12.1333 96.1333 4.40001C80.5333 0.400006 51.4667 -1.06666 40.6667 1.73334Z" fill="currentColor" />
            </svg>
          </div>
          <span class="text-sm font-semibold text-[#f9f9f9]">devleadhunter</span>
        </div>
      </div>
      
      <!-- Main Content -->
      <div class="flex-1 bg-[#050505] p-8 overflow-y-auto">
        <h1 class="text-3xl font-bold text-[#f9f9f9] mb-3">Recherche en cours</h1>
        <p class="text-sm text-[#8b949e] mb-8 font-light">Recherche de prospects en cours...</p>
        
        <div class="bg-transparent rounded-xl border border-[#30363d]/30 p-8 space-y-6">
          <div class="flex items-center justify-between">
            <div class="flex-1">
              <div class="flex items-center gap-3 mb-4">
                <div class="w-2.5 h-2.5 rounded-full bg-[#2BAD5F] animate-pulse"></div>
                <span class="text-base font-medium text-[#f9f9f9]">Recherche active</span>
              </div>
              <div class="h-2.5 bg-[#050505] rounded-full overflow-hidden mb-3">
                <div class="h-full bg-[#2BAD5F] rounded-full transition-all" style="width: 65%"></div>
              </div>
              <p class="text-sm text-[#8b949e] font-light">65% complété - 13 prospects trouvés</p>
            </div>
          </div>
          
          <div class="space-y-3 pt-6 border-t border-[#30363d]/30">
            <div class="flex items-center gap-4 p-4 bg-[#050505] rounded-xl border border-[#30363d]/30">
              <div class="w-10 h-10 rounded-lg bg-[#21262d]/50 flex items-center justify-center">
                <i class="fa-solid fa-building text-[#8b949e] text-base"></i>
              </div>
              <div class="flex-1">
                <div class="text-base font-medium text-[#f9f9f9]">Restaurant Le Gourmet</div>
                <div class="text-sm text-[#8b949e] font-light">Paris, 75001</div>
              </div>
              <div class="text-sm text-[#2BAD5F] bg-[#2BAD5F]/10 px-3 py-1.5 rounded-lg font-medium">Confiance: 3</div>
            </div>
            <div class="flex items-center gap-4 p-4 bg-[#050505] rounded-xl border border-[#30363d]/30">
              <div class="w-10 h-10 rounded-lg bg-[#21262d]/50 flex items-center justify-center">
                <i class="fa-solid fa-building text-[#8b949e] text-base"></i>
              </div>
              <div class="flex-1">
                <div class="text-base font-medium text-[#f9f9f9]">Salon de coiffure Style</div>
                <div class="text-sm text-[#8b949e] font-light">Lyon, 69001</div>
              </div>
              <div class="text-sm text-[#2BAD5F] bg-[#2BAD5F]/10 px-3 py-1.5 rounded-lg font-medium">Confiance: 4</div>
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

