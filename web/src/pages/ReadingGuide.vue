<template>
  <article class="max-w-[720px] mx-auto px-8 py-16">
    <header class="mb-12">
      <p class="text-xs font-semibold tracking-widest uppercase text-ochre mb-3">Reference</p>
      <h1 class="font-serif text-5xl text-forest-dark leading-tight mb-4">Reading Guide</h1>
      <p class="text-lg text-stone leading-relaxed">
        How to read and write Taita words in this dictionary. Plain language, no jargon — if anything here is unclear,
        <RouterLink to="/suggest" class="text-forest hover:underline">tell us</RouterLink>.
      </p>
    </header>

    <!-- TOC -->
    <nav class="bg-cream-50 border border-cream-200 rounded-xl p-5 mb-12 text-sm">
      <p class="text-xs font-semibold uppercase tracking-widest text-stone mb-3">On this page</p>
      <ol class="space-y-1.5 text-ink-soft">
        <li><a href="#s1" class="text-forest hover:underline">1. The sounds we use</a></li>
        <li><a href="#s2" class="text-forest hover:underline">2. How we spell</a></li>
        <li><a href="#s3" class="text-forest hover:underline">3. Plurals</a></li>
        <li><a href="#s4" class="text-forest hover:underline">4. Verbs</a></li>
        <li><a href="#s5" class="text-forest hover:underline">5. When a word is a whole sentence</a></li>
        <li><a href="#s6" class="text-forest hover:underline">6. Why we don't break words apart</a></li>
      </ol>
    </nav>

    <section id="s1" class="mb-12">
      <h2 class="font-serif text-2xl text-forest-dark mb-4">1. The sounds we use</h2>
      <p class="text-base text-ink-soft leading-relaxed mb-4">
        Taita uses the same five vowels as Swahili and English:
      </p>
      <div class="grid grid-cols-5 gap-3 my-6">
        <div class="bg-cream-50 border border-cream-200 rounded-lg p-3 text-center">
          <p class="font-serif text-2xl text-forest-dark">a</p>
          <p class="text-[10px] text-stone mt-1">as in <em>baba</em></p>
        </div>
        <div class="bg-cream-50 border border-cream-200 rounded-lg p-3 text-center">
          <p class="font-serif text-2xl text-forest-dark">e</p>
          <p class="text-[10px] text-stone mt-1">as in <em>nde</em></p>
        </div>
        <div class="bg-cream-50 border border-cream-200 rounded-lg p-3 text-center">
          <p class="font-serif text-2xl text-forest-dark">i</p>
          <p class="text-[10px] text-stone mt-1">as in <em>siku</em></p>
        </div>
        <div class="bg-cream-50 border border-cream-200 rounded-lg p-3 text-center">
          <p class="font-serif text-2xl text-forest-dark">o</p>
          <p class="text-[10px] text-stone mt-1">as in <em>moto</em></p>
        </div>
        <div class="bg-cream-50 border border-cream-200 rounded-lg p-3 text-center">
          <p class="font-serif text-2xl text-forest-dark">u</p>
          <p class="text-[10px] text-stone mt-1">as in <em>nyumba</em></p>
        </div>
      </div>
      <p class="text-base text-ink-soft leading-relaxed mb-4">
        Consonants are mostly the same as Swahili. We write them with ordinary letters — no special characters,
        no diacritics. If you can read Swahili, you can read Taita.
      </p>
      <p class="text-base text-ink-soft leading-relaxed">
        Some sounds vary between dialects (Dawida, Sagala, Kasighau). When a word is pronounced differently in
        different dialects, we list each form. We don't decide which one is "correct" — we record what people
        actually say.
      </p>
    </section>

    <section id="s2" class="mb-12">
      <h2 class="font-serif text-2xl text-forest-dark mb-4">2. How we spell</h2>
      <p class="text-base text-ink-soft leading-relaxed mb-4">A few simple rules:</p>
      <ul class="space-y-3 text-base text-ink-soft leading-relaxed">
        <li class="flex gap-3">
          <span class="text-ochre font-bold">·</span>
          <span><strong>Lowercase</strong> for all words, except proper names (people, places).</span>
        </li>
        <li class="flex gap-3">
          <span class="text-ochre font-bold">·</span>
          <span><strong>Apostrophes</strong> show where a sound has been dropped, e.g. <em>nda</em> for <em>nda</em> ("I want").</span>
        </li>
        <li class="flex gap-3">
          <span class="text-ochre font-bold">·</span>
          <span><strong>Compound words</strong> are written as one word, e.g. <em>mlimani</em> (on the mountain), not <em>mlima ni</em>.</span>
        </li>
        <li class="flex gap-3">
          <span class="text-ochre font-bold">·</span>
          <span>When in doubt, write the word the way you say it. Reviewers can clean up spelling later.</span>
        </li>
      </ul>
    </section>

    <section id="s3" class="mb-12">
      <h2 class="font-serif text-2xl text-forest-dark mb-4">3. Plurals</h2>
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
        <li class="flex gap-3">
          <span class="text-ochre font-bold">·</span>
          <span><strong>m-</strong> becomes <strong>mi-</strong> — e.g. mti → miti (tree → trees)</span>
        </li>
        <li class="flex gap-3">
          <span class="text-ochre font-bold">·</span>
          <span><strong>ki-</strong> becomes <strong>vi-</strong> — e.g. kifumuki → vifumuki (girl → girls)</span>
        </li>
        <li class="flex gap-3">
          <span class="text-ochre font-bold">·</span>
          <span><strong>m-</strong> becomes <strong>w-</strong> — e.g. mwana → wana (child → children)</span>
        </li>
      </ul>
      <p class="text-base text-ink-soft leading-relaxed mt-4">
        There are about ten patterns in total. You don't need to memorize them — when you add a word, just write
        its plural form (if you know it) and the dictionary will link them.
      </p>
    </section>

    <section id="s4" class="mb-12">
      <h2 class="font-serif text-2xl text-forest-dark mb-4">4. Verbs</h2>
      <p class="text-base text-ink-soft leading-relaxed mb-4">
        Taita verbs change shape based on <em>who</em> is doing the action and <em>when</em>. This is also like Swahili.
        For example, the root <em>-lim-</em> (to farm):
      </p>
      <div class="bg-cream-50 border border-cream-200 rounded-xl p-5 my-6 space-y-2 text-sm">
        <div class="flex gap-4">
          <span class="font-serif text-base text-ink w-32">kulima</span>
          <span class="text-stone">to farm (the verb in its basic form)</span>
        </div>
        <div class="flex gap-4">
          <span class="font-serif text-base text-ink w-32">nilima</span>
          <span class="text-stone">I farmed</span>
        </div>
        <div class="flex gap-4">
          <span class="font-serif text-base text-ink w-32">alima</span>
          <span class="text-stone">he/she farmed</span>
        </div>
        <div class="flex gap-4">
          <span class="font-serif text-base text-ink w-32">walima</span>
          <span class="text-stone">they farmed</span>
        </div>
        <div class="flex gap-4">
          <span class="font-serif text-base text-ink w-32">nilimalimia</span>
          <span class="text-stone">I have farmed for someone</span>
        </div>
      </div>
      <p class="text-base text-ink-soft leading-relaxed">
        In this dictionary, we usually list the basic form (starting with <em>ku-</em>) as the main entry. Other
        forms are linked as related words.
      </p>
    </section>

    <section id="s5" class="mb-12">
      <h2 class="font-serif text-2xl text-forest-dark mb-4">5. When a word is a whole sentence</h2>
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

    <section id="s6" class="mb-8">
      <h2 class="font-serif text-2xl text-forest-dark mb-4">6. Why we don't break words apart</h2>
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
        This is a living dictionary. It changes as the language changes.
      </p>
    </section>

    <footer class="mt-12 pt-8 border-t border-cream-200">
      <p class="text-sm text-stone mb-4">Ready to contribute?</p>
      <div class="flex gap-3">
        <RouterLink
          to="/suggest"
          class="bg-forest hover:bg-forest-dark text-cream font-semibold text-sm px-5 py-2.5 rounded-lg transition"
        >
          Suggest a word
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
import { RouterLink } from "vue-router";
</script>
