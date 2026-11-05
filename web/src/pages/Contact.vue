<template>
  <div class="max-w-2xl mx-auto px-8 py-16">
    <header class="mb-8">
      <p class="text-xs font-semibold tracking-widest uppercase text-ochre mb-2">Contact</p>
      <h1 class="font-serif text-4xl text-forest-dark mb-4">Get in touch</h1>
      <p class="text-base text-stone leading-relaxed">
        Questions, feedback, or want to become a reviewer? Send a message — we read everything.
      </p>
    </header>

    <!-- Contact form -->
    <form @submit.prevent="onSubmit" class="space-y-5">
      <div>
        <label class="field-label">Your name <span class="text-stone-light font-normal">(optional)</span></label>
        <input v-model="form.name" type="text" class="field" placeholder="Your name" :disabled="submitting" />
      </div>

      <div>
        <label class="field-label">Email <span class="text-terracotta">*</span></label>
        <input
          v-model="form.email"
          type="email"
          required
          class="field"
          placeholder="you@example.com"
          :disabled="submitting"
        />
      </div>

      <div>
        <label class="field-label">Subject</label>
        <select v-model="form.subject" class="field" :disabled="submitting">
          <option value="general">General question or feedback</option>
          <option value="reviewer">I want to be a reviewer</option>
          <option value="bug">Report a problem</option>
          <option value="other">Other</option>
        </select>
      </div>

      <!-- Custom subject when "Other" is selected -->
      <div v-if="form.subject === 'other'">
        <label class="field-label">Subject line <span class="text-terracotta">*</span></label>
        <input
          v-model="form.customSubject"
          type="text"
          required
          class="field"
          placeholder="What's this about?"
          :disabled="submitting"
        />
      </div>

      <div>
        <label class="field-label">Message <span class="text-terracotta">*</span></label>
        <textarea
          v-model="form.message"
          rows="5"
          required
          class="field"
          placeholder="Write us a short message"
          :disabled="submitting"
        ></textarea>
      </div>

      <!-- Honeypot -->
      <input
        v-model="honeypot"
        type="text"
        name="website"
        style="position: absolute; left: -9999px; opacity: 0; pointer-events: none"
        tabindex="-1"
        autocomplete="off"
      />

      <!-- Error / success -->
      <div
        v-if="error"
        class="bg-terracotta/10 border border-terracotta/30 rounded-lg p-3 text-sm text-terracotta-dark"
      >
        {{ error }}
      </div>

      <div
        v-if="success"
        class="bg-forest/10 border border-forest/30 rounded-lg p-4 text-sm text-forest-dark"
      >
        <p class="font-semibold mb-1">Your email is ready to send!</p>
        <p class="text-xs">Your email app should have opened with your message pre-filled. Just hit send.</p>
        <p class="text-xs text-stone-light mt-2">
          Didn't open? Email us directly at <a href="mailto:mwadayz@yandex.com" class="text-forest hover:underline">mwadayz@yandex.com</a>
        </p>
      </div>

      <!-- "This opens your email app" note -->
      <p class="text-xs text-stone-light">
        Clicking send will open your email app with the message pre-filled.
      </p>

      <button
        type="submit"
        :disabled="submitting"
        class="bg-forest hover:bg-forest-dark text-cream font-semibold text-sm px-6 py-3 rounded-lg transition disabled:opacity-50 flex items-center gap-2"
      >
        <svg v-if="submitting" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        {{ submitting ? "Opening email..." : "Send message" }}
      </button>
    </form>
  </div>
</template>

<script setup>
import { ref, reactive } from "vue";

const form = reactive({
  name: "",
  email: "",
  subject: "general",
  customSubject: "",
  message: "",
});

const honeypot = ref("");
const submitting = ref(false);
const error = ref("");
const success = ref(false);

async function onSubmit() {
  error.value = "";
  success.value = false;

  if (!form.email.trim() || !form.message.trim()) {
    error.value = "Please fill in your email and message.";
    return;
  }

  if (form.subject === "other" && !form.customSubject.trim()) {
    error.value = "Please enter a subject line.";
    return;
  }

  // Honeypot — silently succeed
  if (honeypot.value) {
    success.value = true;
    return;
  }

  submitting.value = true;

  try {
    // Build the email body
    let body = `From: ${form.name || "(no name)"}\n`;
    body += `Email: ${form.email}\n\n`;
    body += `${form.message}\n`;

    const subjectLine =
      form.subject === "reviewer"
        ? "I want to be a reviewer — TaitaLumi"
        : form.subject === "bug"
          ? "Bug report — TaitaLumi"
          : form.subject === "other"
            ? (form.customSubject.trim() || "TaitaLumi: Other")
            : `TaitaLumi: ${form.subject}`;

    const mailtoLink = `mailto:mwadayz@yandex.com?subject=${encodeURIComponent(subjectLine)}&body=${encodeURIComponent(body)}`;

    window.location.href = mailtoLink;

    success.value = true;

    // Reset form
    form.name = "";
    form.email = "";
    form.subject = "general";
    form.customSubject = "";
    form.message = "";
  } catch (err) {
    error.value = "Something went wrong. Please email mwadayz@yandex.com directly.";
  } finally {
    submitting.value = false;
  }
}
</script>

<style scoped>
.field {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid #e8dfc8;
  border-radius: 8px;
  background: #fdfbf6;
  font-size: 14px;
  color: #1f2937;
  font-family: "Inter", sans-serif;
}
.field:focus {
  outline: none;
  border-color: #2d5a3d;
  box-shadow: 0 0 0 3px rgba(45, 90, 61, 0.1);
}
.field:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.field-label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 6px;
  letter-spacing: 0.02em;
}
</style>
