<template>
  <article class="max-w-[720px] mx-auto px-4 md:px-8 py-12 md:py-16">

    <header class="mb-12">
      <p class="text-xs font-semibold tracking-widest uppercase text-ochre mb-3">Reference</p>
      <h1 class="font-serif text-4xl md:text-5xl text-forest-dark leading-tight mb-4">Reading Guide</h1>
      <p class="text-lg text-stone leading-relaxed">How to read and write Taita words in this dictionary. Plain language — if anything is unclear, <RouterLink to="/contact" class="text-forest hover:underline">tell us</RouterLink>.</p>
    </header>

    <!-- TOC -->
    <nav class="bg-cream-50 border border-cream-200 rounded-xl p-5 mb-12 text-sm">
      <p class="text-xs font-semibold uppercase tracking-widest text-stone mb-3">On this page</p>
      <ol class="space-y-1.5 text-ink-soft">
        <li><a href="#s1" class="text-forest hover:underline">1. The alphabet</a></li>
        <li><a href="#s2" class="text-forest hover:underline">2. Vowels</a></li>
        <li><a href="#s3" class="text-forest hover:underline">3. Consonants</a></li>
        <li><a href="#s4" class="text-forest hover:underline">4. The bh / wh / w' question</a></li>
        <li><a href="#s5" class="text-forest hover:underline">5. How we spell</a></li>
        <li><a href="#s6" class="text-forest hover:underline">6. Plurals</a></li>
        <li><a href="#s7" class="text-forest hover:underline">7. Verbs</a></li>
        <li><a href="#s8" class="text-forest hover:underline">8. When a word is a whole sentence</a></li>
        <li><a href="#s9" class="text-forest hover:underline">9. Proper names</a></li>
        <li><a href="#s10" class="text-forest hover:underline">10. Why we don't break words apart</a></li>
      </ol>
    </nav>

    <!-- ═══════════════════════════════════════════════════ -->
    <!-- 1. THE ALPHABET -->
    <!-- ═══════════════════════════════════════════════════ -->

    <section id="s1" class="mb-12">
      <h2 class="font-serif text-2xl text-forest-dark mb-4">1. The alphabet</h2>
      <p class="text-base text-ink-soft leading-relaxed mb-4">
        Taita uses the same basic letters as Swahili and English, plus a few extra sounds that don't exist in Swahili.
        The most important of these is <strong>bh</strong> — the sound you hear in "Bhundanyi" (the town most people spell "Wundanyi").
      </p>
      <p class="text-base text-ink-soft leading-relaxed mb-4">
        We follow the <em>Unified Orthography for Bantu Languages of Kenya</em> (Kioko et al., 2012), which is the published standard for Dawida.
        Where people use different spellings for the same sound, we list the variants but show the preferred form.
      </p>
      <p class="text-base text-ink-soft leading-relaxed">
        The full alphabet has <strong>5 vowels</strong> and <strong>26 consonants</strong> (including digraphs like <em>ch</em>, <em>ny</em>, <em>sh</em>, <em>ng'</em>, and <em>bh</em>).
      </p>
    </section>

    <!-- ═══════════════════════════════════════════════════ -->
    <!-- 2. VOWELS -->
    <!-- ═══════════════════════════════════════════════════ -->

    <section id="s2" class="mb-12">
      <h2 class="font-serif text-2xl text-forest-dark mb-4">2. Vowels</h2>
      <p class="text-base text-ink-soft leading-relaxed mb-4">
        Taita has five vowels — the same as Swahili and English. No special characters, no diacritics.
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
      <p class="text-sm text-stone leading-relaxed">
        If you can read Swahili, you can read Taita vowels.
      </p>
    </section>

    <!-- ═══════════════════════════════════════════════════ -->
    <!-- 3. CONSONANTS -->
    <!-- ═══════════════════════════════════════════════════ -->

    <section id="s3" class="mb-12">
      <h2 class="font-serif text-2xl text-forest-dark mb-4">3. Consonants</h2>
      <p class="text-base text-ink-soft leading-relaxed mb-4">
        Most consonants are the same as Swahili. The ones that need explanation are listed below with examples.
      </p>

      <!-- Consonant table -->
      <div class="overflow-x-auto">
        <table class="w-full text-sm border border-cream-200 rounded-lg overflow-hidden">
          <thead>
            <tr class="bg-cream-100 text-stone">
              <th class="text-left px-4 py-2 font-semibold">Symbol</th>
              <th class="text-left px-4 py-2 font-semibold">Sounds like</th>
              <th class="text-left px-4 py-2 font-semibold">Example</th>
              <th class="text-left px-4 py-2 font-semibold">Notes</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-cream-200">
            <!-- Standard consonants (same as Swahili) -->
            <tr class="bg-cream-50">
              <td class="px-4 py-2 font-serif text-base text-ink">b, d, f, g, h, j, k, l, m, n, p, r, s, t, v, y, z</td>
              <td class="px-4 py-2 text-stone">Same as Swahili</td>
              <td class="px-4 py-2 text-stone">—</td>
              <td class="px-4 py-2 text-stone-light text-xs">No surprises</td>
            </tr>
            <!-- Digraphs -->
            <tr>
              <td class="px-4 py-2 font-serif text-base text-ink">ch</td>
              <td class="px-4 py-2 text-stone">ch in <em>chai</em></td>
              <td class="px-4 py-2 text-stone">—</td>
              <td class="px-4 py-2 text-stone-light text-xs">Same as Swahili</td>
            </tr>
            <tr class="bg-cream-50">
              <td class="px-4 py-2 font-serif text-base text-ink">ny</td>
              <td class="px-4 py-2 text-stone">ny in <em>nyama</em></td>
              <td class="px-4 py-2 text-stone"><em>bhundanyi</em></td>
              <td class="px-4 py-2 text-stone-light text-xs">Same as Swahili</td>
            </tr>
            <tr>
              <td class="px-4 py-2 font-serif text-base text-ink">sh</td>
              <td class="px-4 py-2 text-stone">sh in <em>shule</em></td>
              <td class="px-4 py-2 text-stone">—</td>
              <td class="px-4 py-2 text-stone-light text-xs">Same as Swahili</td>
            </tr>
            <tr class="bg-cream-50">
              <td class="px-4 py-2 font-serif text-base text-ink">ng'</td>
              <td class="px-4 py-2 text-stone">ng' in <em>ng'ombe</em></td>
              <td class="px-4 py-2 text-stone">—</td>
              <td class="px-4 py-2 text-stone-light text-xs">The apostrophe matters: ng' ≠ ng</td>
            </tr>
            <!-- Taita-specific sounds -->
            <tr class="bg-ochre/5">
              <td class="px-4 py-2 font-serif text-base text-terracotta">bh</td>
              <td class="px-4 py-2 text-stone">No Swahili equivalent. A buzzing sound made with both lips.</td>
              <td class="px-4 py-2 text-stone"><em>bhake</em> (their)<br><em>bhundanyi</em> (Wundanyi)</td>
              <td class="px-4 py-2 text-terracotta text-xs font-medium">Preferred form. See section 4.</td>
            </tr>
            <tr class="bg-ochre/5">
              <td class="px-4 py-2 font-serif text-base text-terracotta">gh</td>
              <td class="px-4 py-2 text-stone">gh in <em>ghali</em> (a raspy g)</td>
              <td class="px-4 py-2 text-stone"><em>aighu</em> (up/above)</td>
              <td class="px-4 py-2 text-stone-light text-xs">Rare in Swahili, used in Taita</td>
            </tr>
            <tr class="bg-ochre/5">
              <td class="px-4 py-2 font-serif text-base text-terracotta">jh</td>
              <td class="px-4 py-2 text-stone">No Swahili equivalent. Between j and zh.</td>
              <td class="px-4 py-2 text-stone"><em>jhaa</em> (to eat)</td>
              <td class="px-4 py-2 text-stone-light text-xs">Some dialects use plain j. We use jh.</td>
            </tr>
            <tr class="bg-ochre/5">
              <td class="px-4 py-2 font-serif text-base text-terracotta">w</td>
              <td class="px-4 py-2 text-stone">w in <em>wake</em> (his/her)</td>
              <td class="px-4 py-2 text-stone"><em>wake</em> (his/her)</td>
              <td class="px-4 py-2 text-stone-light text-xs">Plain w only — NOT the bh sound</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="text-xs text-stone-light mt-3 italic">
        Sounds marked in orange are the ones that differ from Swahili or cause confusion.
      </p>
    </section>

    <!-- ═══════════════════════════════════════════════════ -->
    <!-- 4. THE bh / wh / w' QUESTION -->
    <!-- ═══════════════════════════════════════════════════ -->

    <section id="s4" class="mb-12">
      <h2 class="font-serif text-2xl text-forest-dark mb-4">4. The bh / wh / w' question</h2>
      <p class="text-base text-ink-soft leading-relaxed mb-4">
        This is the most common source of confusion in Taita spelling. There's a sound in Taita that
        doesn't exist in Swahili — a buzzing sound made with both lips. You hear it in the name of the
        town <strong>Bhundanyi</strong> (usually spelled "Wundanyi").
      </p>
      <p class="text-base text-ink-soft leading-relaxed mb-4">
        Over the years, people have written this sound three different ways:
      </p>
      <div class="bg-cream-50 border border-cream-200 rounded-xl p-5 my-6 space-y-4">
        <div class="flex gap-4">
          <span class="font-serif text-2xl text-forest font-bold w-12">bh</span>
          <div>
            <p class="text-sm text-ink"><strong>What we use.</strong> This is the form published in the Unified Orthography for Bantu Languages of Kenya (2012).</p>
            <p class="text-xs text-stone mt-1">Example: <em>bhake</em> (their), <em>bhundanyi</em> (Wundanyi)</p>
          </div>
        </div>
        <div class="flex gap-4">
          <span class="font-serif text-2xl text-stone w-12">wh</span>
          <div>
            <p class="text-sm text-ink"><strong>Old convention.</strong> Used in earlier editing of this dictionary. Maps to bh.</p>
            <p class="text-xs text-stone mt-1">Example: <em>whake</em> → <em>bhake</em></p>
          </div>
        </div>
        <div class="flex gap-4">
          <span class="font-serif text-2xl text-stone w-12">w'</span>
          <div>
            <p class="text-sm text-ink"><strong>Some writers use this.</strong> Maps to bh, but the apostrophe is also used for other sounds, so we don't swap it automatically.</p>
            <p class="text-xs text-stone mt-1">Example: <em>w'ake</em> → <em>bhake</em></p>
          </div>
        </div>
      </div>
      <p class="text-base text-ink-soft leading-relaxed mb-4">
        <strong>What TaitaLumi prefers:</strong> We use <strong>bh</strong>. If you see <em>wh</em> or <em>w'</em> in the dictionary,
        it's from older data and will be updated. When you contribute, please use <em>bh</em>.
      </p>
      <p class="text-base text-ink-soft leading-relaxed">
        <strong>Why it matters:</strong> <em>wake</em> means "his/her" (singular). <em>bhake</em> means "their" (plural).
        They sound different and mean different things — writing them the same way loses that distinction.
      </p>
    </section>

    <!-- ═══════════════════════════════════════════════════ -->
    <!-- 5. HOW WE SPELL -->
    <!-- ═══════════════════════════════════════════════════ -->

    <section id="s5" class="mb-12">
      <h2 class="font-serif text-2xl text-forest-dark mb-4">5. How we spell</h2>
      <p class="text-base text-ink-soft leading-relaxed mb-4">A few simple rules:</p>
      <ul class="space-y-3 text-base text-ink-soft leading-relaxed">
        <li class="flex gap-3">
          <span class="text-ochre font-bold">·</span>
          <span><strong>Lowercase</strong> for all words, except proper names (people, places).</span>
        </li>
        <li class="flex gap-3">
          <span class="text-ochre font-bold">·</span>
          <span><strong>Use bh</strong> for the buzzing lip sound — not wh or w'.</span>
        </li>
        <li class="flex gap-3">
          <span class="text-ochre font-bold">·</span>
          <span><strong>ng' with an apostrophe</strong> for the sound in <em>ng'ombe</em>. Plain <em>ng</em> is a different sound (as in <em>ngozi</em>).</span>
        </li>
        <li class="flex gap-3">
          <span class="text-ochre font-bold">·</span>
          <span><strong>Compound words</strong> are written as one word: <em>mlimani</em> (on the mountain), not <em>mlima ni</em>.</span>
        </li>
        <li class="flex gap-3">
          <span class="text-ochre font-bold">·</span>
          <span>When in doubt, write the word the way you say it. Reviewers can clean up spelling later.</span>
        </li>
      </ul>
    </section>

    <!-- ═══════════════════════════════════════════════════ -->
    <!-- 6. PLURALS -->
    <!-- ═══════════════════════════════════════════════════ -->

    <section id="s6" class="mb-12">
      <h2 class="font-serif text-2xl text-forest-dark mb-4">6. Plurals</h2>
      <p class="text-base text-ink-soft leading-relaxed mb-4">
        Many Taita words change their beginning to mean more than one. This is the same pattern as Swahili.
      </p>
      <div class="bg-cream-50 border border-cream-200 rounded-xl p-5 my-6">
        <div class="grid grid-cols-3 gap-4 text-sm">
          <div>
            <p class="text-[10px] uppercase tracking-wider text-stone mb-1">One</p>
            <p class="font-serif text-xl text-ink">mlima</p>
            <p class="text-xs text-stone">mountain</p>
          </div>
          <div class="text-center text-stone-light pt-4">→</div>
          <div>
            <p class="text-[10px] uppercase tracking-wider text-stone mb-1">Many</p>
            <p class="font-serif text-xl text-ink">milima</p>
            <p class="text-xs text-stone">mountains</p>
          </div>
        </div>
      </div>
      <p class="text-base text-ink-soft leading-relaxed mb-4">A few common patterns:</p>
      <ul class="space-y-2 text-base text-ink-soft leading-relaxed">
        <li class="flex gap-3"><span class="text-ochre font-bold">·</span><span><strong>m-</strong> becomes <strong>mi-</strong> — e.g. mti → miti (tree → trees)</span></li>
        <li class="flex gap-3"><span class="text-ochre font-bold">·</span><span><strong>ki-</strong> becomes <strong>vi-</strong> — e.g. kifumuki → vifumuki (girl → girls)</span></li>
        <li class="flex gap-3"><span class="text-ochre font-bold">·</span><span><strong>m-</strong> becomes <strong>w-</strong> — e.g. mwana → wana (child → children)</span></li>
      </ul>
      <p class="text-base text-ink-soft leading-relaxed mt-4">
        There are about ten patterns in total. You don't need to memorize them — when you add a word, just write
        its plural form (if you know it) and the dictionary will link them.
      </p>
    </section>

    <!-- ═══════════════════════════════════════════════════ -->
    <!-- 7. VERBS -->
    <!-- ═══════════════════════════════════════════════════ -->

    <section id="s7" class="mb-12">
      <h2 class="font-serif text-2xl text-forest-dark mb-4">7. Verbs</h2>
      <p class="text-base text-ink-soft leading-relaxed mb-4">
        Taita verbs change shape based on <em>who</em> is doing the action and <em>when</em>. This is also like Swahili.
        For example, the root <em>-lim-</em> (to farm):
      </p>
      <div class="bg-cream-50 border border-cream-200 rounded-xl p-5 my-6 space-y-2 text-sm">
        <div class="flex gap-4"><span class="font-serif text-base text-ink w-32">kulima</span><span class="text-stone">to farm (the verb in its basic form)</span></div>
        <div class="flex gap-4"><span class="font-serif text-base text-ink w-32">nilima</span><span class="text-stone">I farmed</span></div>
        <div class="flex gap-4"><span class="font-serif text-base text-ink w-32">alima</span><span class="text-stone">he/she farmed</span></div>
        <div class="flex gap-4"><span class="font-serif text-base text-ink w-32">walima</span><span class="text-stone">they farmed</span></div>
        <div class="flex gap-4"><span class="font-serif text-base text-ink w-32">nilimalimia</span><span class="text-stone">I have farmed for someone</span></div>
      </div>
      <p class="text-base text-ink-soft leading-relaxed">
        In this dictionary, we usually list the basic form (starting with <em>ku-</em>) as the main entry. Other
        forms are linked as related words.
      </p>
    </section>

    <!-- ═══════════════════════════════════════════════════ -->
    <!-- 8. WHEN A WORD IS A WHOLE SENTENCE -->
    <!-- ═══════════════════════════════════════════════════ -->

    <section id="s8" class="mb-12">
      <h2 class="font-serif text-2xl text-forest-dark mb-4">8. When a word is a whole sentence</h2>
      <p class="text-base text-ink-soft leading-relaxed mb-4">
        Some Taita words pack a lot of meaning into one word. A single word can mean what would be a full sentence
        in English.
      </p>
      <div class="bg-cream-50 border border-cream-200 rounded-xl p-5 my-6">
        <p class="font-serif text-3xl text-forest-dark mb-2">nimlimia</p>
        <p class="text-base text-ink mb-1"><strong>"I have climbed for him/her."</strong></p>
        <p class="text-sm text-stone">
          This single word contains: the doer (I), the action (climb), the timing (have done), and the person who
          benefits (him/her).
        </p>
      </div>
      <p class="text-base text-ink-soft leading-relaxed mb-4">
        If you speak Swahili, this will feel familiar — Swahili does the same thing. English just uses more
        separate words.
      </p>
      <p class="text-base text-ink-soft leading-relaxed">
        For these words, the dictionary gives a plain translation ("I have climbed for him/her"), not a
        piece-by-piece breakdown. We don't try to slice the word into parts — we just tell you what it means.
      </p>
    </section>

    <!-- ═══════════════════════════════════════════════════ -->
    <!-- 9. PROPER NAMES -->
    <!-- ═══════════════════════════════════════════════════ -->

    <section id="s9" class="mb-12">
      <h2 class="font-serif text-2xl text-forest-dark mb-4">9. Proper names</h2>
      <p class="text-base text-ink-soft leading-relaxed mb-4">
        Place names and personal names are tricky. The town most people call "Wundanyi" should, by the rules
        of this dictionary, be spelled <strong>Bhundanyi</strong> — because that first sound is the bh sound,
        not a plain w.
      </p>
      <p class="text-base text-ink-soft leading-relaxed mb-4">
        <strong>What TaitaLumi does:</strong> We use the standard spelling (<em>bhundanyi</em>) in word entries.
        But we understand that conventional spellings ("Wundanyi") are what people actually search for.
        When the search system is updated, it will find <em>bhundanyi</em> even if you type <em>wundanyi</em>.
      </p>
      <p class="text-base text-ink-soft leading-relaxed">
        For now, if you can't find a word, try the other spelling.
      </p>
    </section>

    <!-- ═══════════════════════════════════════════════════ -->
    <!-- 10. WHY WE DON'T BREAK WORDS APART -->
    <!-- ═══════════════════════════════════════════════════ -->

    <section id="s10" class="mb-8">
      <h2 class="font-serif text-2xl text-forest-dark mb-4">10. Why we don't break words apart</h2>
      <p class="text-base text-ink-soft leading-relaxed mb-4">
        This dictionary documents how people actually use Taita. It does not prescribe rules. There is no official
        Taita orthography in Kenya today, and we don't pretend there is one.
      </p>
      <p class="text-base text-ink-soft leading-relaxed mb-4">
        So when you see a word spelled differently from how you'd write it, that's not a mistake — it's a record
        of how someone says it. You can suggest an alternative spelling, and the community can vote on which one
        to feature.
      </p>
      <p class="text-base text-ink-soft leading-relaxed">
        That said, we do have preferences (like <em>bh</em> over <em>wh</em>) based on the published unified orthography.
        These preferences are explained in this guide so you know what to expect.
      </p>
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
