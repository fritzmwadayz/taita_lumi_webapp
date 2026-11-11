<template>
  <div>
    <!-- Header -->
    <section class="px-4 md:px-12 py-12 md:py-16 text-center border-b border-cream-200">
      <p class="text-xs font-semibold tracking-widest uppercase text-ochre mb-3">
        Support the project
      </p>
      <h1 class="font-serif text-3xl md:text-5xl text-forest-dark leading-tight mb-4 max-w-3xl mx-auto">
        Keep Lumi growing.
      </h1>
      <p class="text-sm md:text-base text-stone leading-relaxed max-w-2xl mx-auto">
        Lumi is a free, open-source project built by volunteers. There are two ways to help:
        contribute your time as a reviewer, or contribute financially.
      </p>
    </section>

    <!-- Two paths -->
    <section class="px-4 md:px-12 py-8 md:py-12">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6 md:gap-8 max-w-5xl mx-auto">
        <!-- Become a reviewer -->
        <div class="bg-forest text-cream rounded-2xl p-6 md:p-8 relative overflow-hidden tri-pattern">
          <div class="relative">
            <div class="w-12 h-12 rounded-lg bg-ochre flex items-center justify-center mb-4">
              <svg class="w-6 h-6 text-forest-dark" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                />
              </svg>
            </div>
            <h2 class="font-serif text-2xl text-cream mb-2">Become a reviewer</h2>
            <p class="text-sm text-cream/80 mb-6">
              Reviewers can add words directly to the dictionary, review community suggestions,
              and help shape how Taita is documented. It's the most valuable way to contribute.
            </p>

            <div class="space-y-3 mb-6">
              <div class="flex items-start gap-2 text-sm text-cream/90">
                <svg class="w-4 h-4 mt-0.5 text-ochre-light flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M16.7 5.3a1 1 0 010 1.4l-8 8a1 1 0 01-1.4 0l-4-4a1 1 0 011.4-1.4L8 12.6l7.3-7.3a1 1 0 011.4 0z" />
                </svg>
                <span>Add words that go live immediately</span>
              </div>
              <div class="flex items-start gap-2 text-sm text-cream/90">
                <svg class="w-4 h-4 mt-0.5 text-ochre-light flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M16.7 5.3a1 1 0 010 1.4l-8 8a1 1 0 01-1.4 0l-4-4a1 1 0 011.4-1.4L8 12.6l7.3-7.3a1 1 0 011.4 0z" />
                </svg>
                <span>Review and approve community suggestions</span>
              </div>
              <div class="flex items-start gap-2 text-sm text-cream/90">
                <svg class="w-4 h-4 mt-0.5 text-ochre-light flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M16.7 5.3a1 1 0 010 1.4l-8 8a1 1 0 01-1.4 0l-4-4a1 1 0 011.4-1.4L8 12.6l7.3-7.3a1 1 0 011.4 0z" />
                </svg>
                <span>Help preserve Taita for future generations</span>
              </div>
            </div>

            <NuxtLink
              to="/contact"
              class="focus-ring inline-block bg-ochre hover:bg-ochre-light text-forest-dark font-semibold text-sm px-5 py-2.5 rounded-md transition"
            >
              Apply to be a reviewer →
            </NuxtLink>
          </div>
        </div>

        <!-- Donate -->
        <div class="bg-white border border-cream-200 rounded-2xl p-6 md:p-8">
          <div class="w-12 h-12 rounded-lg bg-forest flex items-center justify-center mb-4">
            <svg class="w-6 h-6 text-cream" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1"
              />
            </svg>
          </div>
          <h2 class="font-serif text-2xl text-forest-dark mb-2">Or donate</h2>
          <p class="text-sm text-stone mb-6">
            Help cover hosting costs and keep the dictionary online. Any amount is appreciated.
          </p>

          <div class="space-y-3">
            <div class="bg-cream-50 border border-cream-200 rounded-lg p-4 flex items-center gap-4">
              <div class="w-10 h-10 rounded-lg bg-[#4CAF50] flex items-center justify-center flex-shrink-0">
                <span class="text-white font-bold">M</span>
              </div>
              <div class="flex-1">
                <p class="text-sm font-semibold text-ink">M-Pesa</p>
                <p class="text-xs text-stone">Send to <span class="font-mono">0718 178 317</span></p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Thank you -->
    <section class="px-4 md:px-12 py-8 md:py-10 bg-cream-50 border-t border-cream-200 text-center">
      <p class="text-sm text-stone">
        Thank you to everyone who supports Lumi — whether through a donation, a word suggestion,
        or just sharing the dictionary with someone who speaks Taita.
      </p>
    </section>
  </div>
</template>

<script setup lang="ts">
// Ported from src/pages/Support.vue — mostly static content.
// RouterLink → NuxtLink (auto-imported).

// ── SEO ───────────────────────────────────────────────────────────────────
useSiteSeo({
  title: 'Support',
  description: 'Support the Lumi Taita dictionary. Become a reviewer or contribute financially to help grow this free, open-source community resource.',
})
</script>
