<template>
  <div>
    <!-- Header -->
    <section class="px-12 py-16 text-center border-b border-cream-200">
      <p class="text-xs font-semibold tracking-widest uppercase text-ochre mb-3">Support the project</p>
      <h1 class="font-serif text-5xl text-forest-dark leading-tight mb-4 max-w-3xl mx-auto">
        Keep the dictionary free and growing.
      </h1>
      <p class="text-base text-stone leading-relaxed max-w-2xl mx-auto">
        TaitaLumi is a free, open-source project run by volunteers. Your support helps us keep the dictionary
        online, reach more speakers, and eventually pay contributors for high-quality entries.
      </p>
    </section>

    <!-- Payment methods -->
    <section class="px-12 py-12">
      <h2 class="text-xs font-semibold uppercase tracking-widest text-stone mb-6 text-center">
        Choose a way to give
      </h2>

      <div class="grid grid-cols-3 gap-5 max-w-5xl mx-auto">
        <!-- M-Pesa -->
        <div class="bg-white border border-cream-200 rounded-xl p-6 text-center hover:border-forest transition">
          <div class="w-12 h-12 mx-auto mb-4 rounded-lg bg-[#4CAF50] flex items-center justify-center">
            <span class="text-white font-bold text-lg">M</span>
          </div>
          <h3 class="font-serif text-xl text-ink mb-1">M-Pesa</h3>
          <p class="text-xs text-stone mb-4">Best for Kenya</p>
          <div class="bg-cream-50 border border-cream-200 rounded-lg p-3 mb-3">
            <p class="text-[10px] uppercase tracking-wider text-stone mb-1">Paybill</p>
            <p class="font-mono text-base font-semibold text-ink">247247</p>
            <p class="text-[10px] uppercase tracking-wider text-stone mt-2 mb-1">Account</p>
            <p class="font-mono text-sm text-ink">TaitaLumi</p>
          </div>
          <p class="text-[10px] text-stone-light">All amounts welcome.</p>
        </div>

        <!-- PayPal -->
        <div class="bg-white border border-cream-200 rounded-xl p-6 text-center hover:border-forest transition">
          <div class="w-12 h-12 mx-auto mb-4 rounded-lg bg-[#003087] flex items-center justify-center">
            <span class="text-white font-bold text-lg">P</span>
          </div>
          <h3 class="font-serif text-xl text-ink mb-1">PayPal</h3>
          <p class="text-xs text-stone mb-4">International</p>
          <div class="bg-cream-50 border border-cream-200 rounded-lg p-3 mb-3">
            <p class="text-[10px] uppercase tracking-wider text-stone mb-1">Link</p>
            <p class="font-mono text-sm text-forest underline">paypal.me/taitalumi</p>
          </div>
          <a
            href="https://paypal.me/taitalumi"
            target="_blank"
            rel="noopener"
            class="text-xs font-semibold text-forest hover:underline"
          >
            Donate via PayPal →
          </a>
        </div>

        <!-- GitHub Sponsors -->
        <div class="bg-white border border-cream-200 rounded-xl p-6 text-center hover:border-forest transition">
          <div class="w-12 h-12 mx-auto mb-4 rounded-lg bg-[#1F2937] flex items-center justify-center">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="white">
              <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.4 3-.405 1.02.005 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12" />
            </svg>
          </div>
          <h3 class="font-serif text-xl text-ink mb-1">GitHub Sponsors</h3>
          <p class="text-xs text-stone mb-4">Recurring or one-time</p>
          <div class="bg-cream-50 border border-cream-200 rounded-lg p-3 mb-3">
            <p class="text-[10px] uppercase tracking-wider text-stone mb-1">Profile</p>
            <p class="font-mono text-sm text-forest underline">github.com/sponsors/fritzmwadayz</p>
          </div>
          <a
            href="https://github.com/sponsors/fritzmwadayz"
            target="_blank"
            rel="noopener"
            class="text-xs font-semibold text-forest hover:underline"
          >
            Sponsor on GitHub →
          </a>
        </div>
      </div>
    </section>

    <!-- Where donations go -->
    <section class="px-12 py-12 bg-cream-50 border-t border-cream-200">
      <div class="max-w-3xl mx-auto">
        <h2 class="font-serif text-2xl text-forest-dark mb-6 text-center">Where your donations go</h2>
        <div class="space-y-3">
          <div class="flex items-center gap-4 bg-white border border-cream-200 rounded-lg p-4">
            <div class="w-10 h-10 rounded-lg bg-cream-100 flex items-center justify-center flex-shrink-0">
              <svg class="w-5 h-5 text-forest" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2" />
              </svg>
            </div>
            <div class="flex-1">
              <p class="text-sm font-semibold text-ink">Hosting & infrastructure</p>
              <p class="text-xs text-stone">
                Render (API), Neon (database), Netlify (frontend). Free tiers for now; paid tiers as we grow.
              </p>
            </div>
            <p class="text-sm font-mono text-forest-dark font-semibold">~$0/mo</p>
          </div>

          <div class="flex items-center gap-4 bg-white border border-cream-200 rounded-lg p-4">
            <div class="w-10 h-10 rounded-lg bg-cream-100 flex items-center justify-center flex-shrink-0">
              <svg class="w-5 h-5 text-forest" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9" />
              </svg>
            </div>
            <div class="flex-1">
              <p class="text-sm font-semibold text-ink">Domain renewal</p>
              <p class="text-xs text-stone">taitalumi.org — annual.</p>
            </div>
            <p class="text-sm font-mono text-forest-dark font-semibold">~$15/yr</p>
          </div>

          <div class="flex items-center gap-4 bg-white border border-cream-200 rounded-lg p-4">
            <div class="w-10 h-10 rounded-lg bg-cream-100 flex items-center justify-center flex-shrink-0">
              <svg class="w-5 h-5 text-forest" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M11 5.882V19.24a1.76 1.76 0 01-3.417.592l-2.147-6.15M18 13a3 3 0 100-6M5.436 13.683A4.001 4.001 0 017 6a1.76 1.76 0 013.417-.592L12 10" />
              </svg>
            </div>
            <div class="flex-1">
              <p class="text-sm font-semibold text-ink">Community outreach</p>
              <p class="text-xs text-stone">X posts, WhatsApp groups, local Taita community events.</p>
            </div>
            <p class="text-sm font-mono text-forest-dark font-semibold">~$20/mo</p>
          </div>

          <div class="flex items-center gap-4 bg-white border border-cream-200 rounded-lg p-4">
            <div class="w-10 h-10 rounded-lg bg-cream-100 flex items-center justify-center flex-shrink-0">
              <svg class="w-5 h-5 text-forest" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
            </div>
            <div class="flex-1">
              <p class="text-sm font-semibold text-ink">Future: contributor stipends</p>
              <p class="text-xs text-stone">
                Once we hit a stable monthly budget, we want to pay top contributors for high-quality entries.
              </p>
            </div>
            <p class="text-sm font-mono text-stone-light font-semibold">Planned</p>
          </div>
        </div>
      </div>
    </section>

    <!-- Transparency note -->
    <section class="px-12 py-10 bg-forest text-cream text-center">
      <div class="max-w-2xl mx-auto">
        <h3 class="font-serif text-xl text-cream mb-2">Full transparency</h3>
        <p class="text-sm text-cream/80 leading-relaxed mb-4">
          We publish a quarterly report of every donation received and how it was spent. Reports are linked from
          the GitHub repo and announced on X.
        </p>
        <a
          href="#"
          class="inline-flex items-center gap-1.5 text-xs font-semibold text-ochre-light hover:text-cream"
        >
          See the latest quarterly report
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
          </svg>
        </a>
      </div>
    </section>

    <!-- Footer -->
    <section class="px-12 py-8 border-t border-cream-200 bg-cream-50 text-center">
      <p class="text-xs text-stone">
        TaitaLumi is a volunteer-run project · MIT licensed · Not a registered charity (donations are not tax-deductible)
      </p>
    </section>
  </div>
</template>

<script setup>
// Static content — no script needed
</script>
