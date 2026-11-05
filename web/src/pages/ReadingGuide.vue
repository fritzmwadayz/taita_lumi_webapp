<template>
  <article class="max-w-[720px] mx-auto px-4 md:px-8 py-12 md:py-16">

    <header class="mb-12">
      <p class="text-xs font-semibold tracking-widest uppercase text-ochre mb-3">Reference</p>
      <h1 class="font-serif text-4xl md:text-5xl text-forest-dark leading-tight mb-4">Reading Guide</h1>
      <p class="text-lg text-stone leading-relaxed">How to read and write Taita words in this dictionary.</p>
    </header>

    <!-- ═══════════════════════════════════════════════════ -->
    <!-- 1. INTRODUCTION -->
    <!-- ═══════════════════════════════════════════════════ -->

    <section id="s1" class="mb-12">
      <p class="text-base text-ink-soft leading-relaxed mb-4">
        Taita has <strong>5 vowels</strong> and <strong>25 consonants</strong> — most of them the same as Swahili.
        Two extra sounds, <em>dh</em> and <em>th</em>, appear in words borrowed from Swahili but are not native to Taita.
      </p>
      <p class="text-base text-ink-soft leading-relaxed mb-4">
        We follow the <em>Unified Orthography for Bantu Languages of Kenya</em> (Kioko et al., 2012), which is the
        published standard for Dawida. Where people use different spellings for the same sound, we list the variants
        but show the preferred form.
      </p>
      <p class="text-base text-ink-soft leading-relaxed">
        If you can read Swahili, you can read most of Taita. The sounds that need explanation are covered below.
      </p>
    </section>

    <!-- ═══════════════════════════════════════════════════ -->
    <!-- 2. VOWELS -->
    <!-- ═══════════════════════════════════════════════════ -->

    <section id="s2" class="mb-12">
      <h2 class="font-serif text-2xl text-forest-dark mb-4">Vowels</h2>
      <p class="text-base text-ink-soft leading-relaxed mb-4">
        Five vowels — the same as Swahili and English. No special characters, no diacritics.
      </p>
      <div class="grid grid-cols-5 gap-3 my-6">
        <div class="bg-cream-50 border border-cream-200 rounded-lg p-3 text-center">
          <p class="font-serif text-3xl text-forest-dark">a</p>
          <p class="text-[10px] text-stone mt-1">as in <em>baba</em></p>
        </div>
        <div class="bg-cream-50 border border-cream-200 rounded-lg p-3 text-center">
          <p class="font-serif text-3xl text-forest-dark">e</p>
          <p class="text-[10px] text-stone mt-1">as in <em>sema</em></p>
        </div>
        <div class="bg-cream-50 border border-cream-200 rounded-lg p-3 text-center">
          <p class="font-serif text-3xl text-forest-dark">i</p>
          <p class="text-[10px] text-stone mt-1">as in <em>siri</em></p>
        </div>
        <div class="bg-cream-50 border border-cream-200 rounded-lg p-3 text-center">
          <p class="font-serif text-3xl text-forest-dark">o</p>
          <p class="text-[10px] text-stone mt-1">as in <em>moto</em></p>
        </div>
        <div class="bg-cream-50 border border-cream-200 rounded-lg p-3 text-center">
          <p class="font-serif text-3xl text-forest-dark">u</p>
          <p class="text-[10px] text-stone mt-1">as in <em>nyumba</em></p>
        </div>
      </div>
    </section>

    <!-- ═══════════════════════════════════════════════════ -->
    <!-- 3. CONSONANTS -->
    <!-- ═══════════════════════════════════════════════════ -->

    <section id="s3" class="mb-12">
      <h2 class="font-serif text-2xl text-forest-dark mb-4">Consonants</h2>
      <p class="text-base text-ink-soft leading-relaxed mb-4">
        Most consonants are the same as Swahili. The table below lists all 25 native consonants plus
        2 borrowed sounds. Sounds marked in orange differ from Swahili or cause confusion.
      </p>

      <div class="overflow-x-auto">
        <table class="w-full text-sm border border-cream-200 rounded-lg overflow-hidden">
          <thead>
            <tr class="bg-cream-100 text-stone">
              <th class="text-left px-3 py-2 font-semibold">Symbol</th>
              <th class="text-left px-3 py-2 font-semibold">Sounds like</th>
              <th class="text-left px-3 py-2 font-semibold">Example</th>
              <th class="text-left px-3 py-2 font-semibold">Meaning</th>
              <th class="text-left px-3 py-2 font-semibold hidden md:table-cell">Notes</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-cream-200">
            <!-- Standard consonants -->
            <tr class="bg-cream-50">
              <td class="px-3 py-2 font-serif text-base text-ink">b, d, f, g, h, j, k, l, m, n, p, r, s, t, v, y, z</td>
              <td class="px-3 py-2 text-stone">Same as Swahili</td>
              <td class="px-3 py-2 text-stone">—</td>
              <td class="px-3 py-2 text-stone">—</td>
              <td class="px-3 py-2 text-stone-light text-xs hidden md:table-cell">No surprises</td>
            </tr>
            <!-- Digraphs -->
            <tr>
              <td class="px-3 py-2 font-serif text-base text-ink">ch</td>
              <td class="px-3 py-2 text-stone">ch in <em>chai</em></td>
              <td class="px-3 py-2 text-stone">—</td>
              <td class="px-3 py-2 text-stone">—</td>
              <td class="px-3 py-2 text-stone-light text-xs hidden md:table-cell">Digraph</td>
            </tr>
            <tr class="bg-cream-50">
              <td class="px-3 py-2 font-serif text-base text-ink">ny</td>
              <td class="px-3 py-2 text-stone">ny in <em>nyama</em></td>
              <td class="px-3 py-2 text-stone">—</td>
              <td class="px-3 py-2 text-stone">—</td>
              <td class="px-3 py-2 text-stone-light text-xs hidden md:table-cell">Digraph</td>
            </tr>
            <tr>
              <td class="px-3 py-2 font-serif text-base text-ink">sh</td>
              <td class="px-3 py-2 text-stone">sh in <em>shule</em></td>
              <td class="px-3 py-2 text-stone">—</td>
              <td class="px-3 py-2 text-stone">—</td>
              <td class="px-3 py-2 text-stone-light text-xs hidden md:table-cell">Digraph</td>
            </tr>
            <tr class="bg-cream-50">
              <td class="px-3 py-2 font-serif text-base text-ink">ng'</td>
              <td class="px-3 py-2 text-stone">ng' in <em>ng'ombe</em></td>
              <td class="px-3 py-2 text-stone">—</td>
              <td class="px-3 py-2 text-stone">—</td>
              <td class="px-3 py-2 text-stone-light text-xs hidden md:table-cell">Apostrophe matters: ng' ≠ ng</td>
            </tr>
            <!-- Taita-specific sounds -->
            <tr class="bg-ochre/5">
              <td class="px-3 py-2 font-serif text-base text-terracotta">gh</td>
              <td class="px-3 py-2 text-stone">gh in <em>ghali</em> (a raspy g)</td>
              <td class="px-3 py-2 text-stone"><em>ighu</em></td>
              <td class="px-3 py-2 text-stone">juu (up / above)</td>
              <td class="px-3 py-2 text-stone-light text-xs hidden md:table-cell">Rare in Swahili</td>
            </tr>
            <tr class="bg-ochre/5">
              <td class="px-3 py-2 font-serif text-base text-terracotta">w</td>
              <td class="px-3 py-2 text-stone">w in <em>wapi</em></td>
              <td class="px-3 py-2 text-stone"><em>wacha</em></td>
              <td class="px-3 py-2 text-stone">amekuja (he/she has come)</td>
              <td class="px-3 py-2 text-stone-light text-xs hidden md:table-cell">Plain w only — NOT the bh sound</td>
            </tr>
            <tr class="bg-ochre/5">
              <td class="px-3 py-2 font-serif text-base text-terracotta">bh</td>
              <td class="px-3 py-2 text-stone">No Swahili equivalent. A buzzing sound with both lips.</td>
              <td class="px-3 py-2 text-stone"><em>Bhaka</em></td>
              <td class="px-3 py-2 text-stone">wanawake (women)</td>
              <td class="px-3 py-2 text-terracotta text-xs font-medium hidden md:table-cell">Preferred form. See section 4.</td>
            </tr>
            <tr class="bg-ochre/5">
              <td class="px-3 py-2 font-serif text-base text-terracotta">jh</td>
              <td class="px-3 py-2 text-stone">Sounds like 's' in <em>measure</em></td>
              <td class="px-3 py-2 text-stone"><em>Kujha</em></td>
              <td class="px-3 py-2 text-stone">kula (to eat)</td>
              <td class="px-3 py-2 text-terracotta text-xs font-medium hidden md:table-cell">Some dialects use j. See section 4.</td>
            </tr>
            <!-- Borrowed sounds -->
            <tr class="bg-stone/5">
              <td class="px-3 py-2 font-serif text-base text-stone">dh</td>
              <td class="px-3 py-2 text-stone">dh in <em>dhiki</em></td>
              <td class="px-3 py-2 text-stone">—</td>
              <td class="px-3 py-2 text-stone">—</td>
              <td class="px-3 py-2 text-stone-light text-xs hidden md:table-cell">Borrowed from Swahili</td>
            </tr>
            <tr class="bg-stone/5">
              <td class="px-3 py-2 font-serif text-base text-stone">th</td>
              <td class="px-3 py-2 text-stone">th in <em>thamani</em></td>
              <td class="px-3 py-2 text-stone">—</td>
              <td class="px-3 py-2 text-stone">—</td>
              <td class="px-3 py-2 text-stone-light text-xs hidden md:table-cell">Borrowed from Swahili</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="text-xs text-stone-light mt-3 italic">
        Orange rows: sounds that differ from Swahili or cause confusion. Grey rows: borrowed sounds.
      </p>
    </section>

    <!-- ═══════════════════════════════════════════════════ -->
    <!-- 4. REGARDING POTENTIAL REPRESENTATION CONFLICTS -->
    <!-- ═══════════════════════════════════════════════════ -->

    <section id="s4" class="mb-8">
      <h2 class="font-serif text-2xl text-forest-dark mb-4">Regarding potential representation conflicts</h2>

      <!-- bh -->
      <div class="mb-8">
        <h3 class="font-serif text-lg text-terracotta mb-3">bh — the buzzing lip sound</h3>
        <p class="text-base text-ink-soft leading-relaxed mb-4">
          Taita has a sound that doesn't exist in Swahili — a buzzing sound made with both lips.
          You hear it in <strong>Bhaka</strong> (women) and in the town name <strong>Bhundanyi</strong>
          (usually spelled "Wundanyi").
        </p>
        <p class="text-base text-ink-soft leading-relaxed mb-4">
          Over the years, people have written this sound three different ways:
        </p>
        <div class="bg-cream-50 border border-cream-200 rounded-xl p-5 my-4 space-y-4">
          <div class="flex gap-4">
            <span class="font-serif text-xl text-forest font-bold w-12 flex-shrink-0">bh</span>
            <div>
              <p class="text-sm text-ink"><strong>What we use.</strong> Published in the Unified Orthography for Bantu Languages of Kenya (2012).</p>
              <p class="text-xs text-stone mt-1">Example: <em>bhaka</em> (women), <em>bhundanyi</em> (Wundanyi)</p>
            </div>
          </div>
          <div class="flex gap-4">
            <span class="font-serif text-xl text-stone w-12 flex-shrink-0">wh</span>
            <div>
              <p class="text-sm text-ink"><strong>Old convention.</strong> Used in earlier editing of this dictionary. Maps to bh.</p>
              <p class="text-xs text-stone mt-1">Example: <em>whake</em> → <em>bhake</em></p>
            </div>
          </div>
          <div class="flex gap-4">
            <span class="font-serif text-xl text-stone w-12 flex-shrink-0">w'</span>
            <div>
              <p class="text-sm text-ink"><strong>Some writers use this.</strong> Maps to bh, but the apostrophe is also used for ng', so we don't swap it automatically.</p>
              <p class="text-xs text-stone mt-1">Example: <em>w'ake</em> → <em>bhake</em></p>
            </div>
          </div>
        </div>
        <p class="text-base text-ink-soft leading-relaxed">
          <strong>What TaitaLumi prefers:</strong> <em>bh</em>. When you contribute, please use <em>bh</em>.
          The distinction matters — <em>wacha</em> (he/she has come) uses plain w, while <em>bhaka</em> (women) uses bh.
          Writing them the same way loses meaning.
        </p>
      </div>

      <!-- jh -->
      <div>
        <h3 class="font-serif text-lg text-terracotta mb-3">jh — a practical compromise</h3>
        <p class="text-base text-ink-soft leading-relaxed mb-4">
          The sound written <strong>jh</strong> doesn't have a clean equivalent in Swahili either.
          It sounds like the 's' in the English word <em>measure</em> — somewhere between j and zh.
          Example: <em>kujha</em> (to eat).
        </p>
        <p class="text-base text-ink-soft leading-relaxed mb-4">
          Some dialects use plain <em>j</em> for this sound. But <em>j</em> is already its own separate
          consonant in Taita (the j in <em>jina</em>), so we can't use it for two different sounds.
          <strong>jh</strong> is a practical solution — not perfect, but it keeps the two sounds distinct.
        </p>
        <div class="bg-cream-50 border border-cream-200 rounded-xl p-5 my-4 space-y-3">
          <div class="flex gap-4">
            <span class="font-serif text-xl text-forest font-bold w-12 flex-shrink-0">jh</span>
            <div>
              <p class="text-sm text-ink"><strong>What we use.</strong> Keeps jh separate from j.</p>
              <p class="text-xs text-stone mt-1">Example: <em>kujha</em> (to eat) ≠ <em>kuja</em> (to come)</p>
            </div>
          </div>
          <div class="flex gap-4">
            <span class="font-serif text-xl text-stone w-12 flex-shrink-0">j</span>
            <div>
              <p class="text-sm text-ink"><strong>Some dialects use this.</strong> But j is already a different sound, so we don't auto-swap.</p>
              <p class="text-xs text-stone mt-1">Treat as a suggestion only, not a replacement.</p>
            </div>
          </div>
        </div>
        <p class="text-base text-ink-soft leading-relaxed">
          <strong>What TaitaLumi prefers:</strong> <em>jh</em>. It's a compromise — a piece of duct tape
          over a gap in the alphabet — but it works. If a better standard emerges, we'll adopt it.
        </p>
      </div>
    </section>

    <!-- Footer CTA -->
    <footer class="mt-12 pt-8 border-t border-cream-200">
      <p class="text-sm text-stone mb-4">Ready to contribute?</p>
      <div class="flex gap-3">
        <RouterLink
          to="/contribute"
          class="bg-forest hover:bg-forest-dark text-cream font-semibold text-sm px-5 py-2.5 rounded-lg transition"
        >
          Contribute
        </RouterLink>
        <RouterLink
          to="/search"
          class="border border-forest text-forest font-semibold text-sm px-5 py-2.5 rounded-lg hover:bg-forest hover:text-cream transition"
        >
          Browse the dictionary
        </RouterLink>
      </div>
    </footer>
  </article>
</template>

<script setup>
import { onMounted } from "vue";
import { RouterLink } from "vue-router";

onMounted(() => {
  localStorage.setItem("taitalumi_guide_visited", "true");
});
</script>
