<template>
  <div class="lock">
    <span class="lock__date">{{ props.dateLabel }}</span>
    <span class="lock__time">{{ props.time }}</span>
    <span v-if="props.isExample" class="lock__example">exemple</span>
    <div class="lock__notification" :class="{ 'lock__notification--new': !props.isExample }" aria-live="polite">
      <div class="lock__app" aria-hidden="true">
        <svg viewBox="0 0 24 24">
          <path
            d="M12 3C6.5 3 2.5 6.6 2.5 11c0 2.4 1.2 4.6 3.2 6.1L5 21l4.4-2.1c.8.2 1.7.3 2.6.3 5.5 0 9.5-3.6 9.5-8.1S17.5 3 12 3Z"
            fill="#fff"
          />
        </svg>
      </div>
      <div class="lock__body">
        <div class="lock__top"><b>Messages</b><span>maintenant</span></div>
        <p class="lock__title">{{ props.assistantName }} · réceptionniste</p>
        <p class="lock__text">{{ props.alertText }}</p>
      </div>
    </div>
    <p class="lock__hint">{{ props.hintText }}</p>
  </div>
</template>

<script lang="ts" setup>
import type { AssistantDemoLockScreenProps } from '~/types/AssistantDemoLockScreen'

const props: AssistantDemoLockScreenProps = defineProps({
  time: {
    type: String,
    required: true,
  },
  dateLabel: {
    type: String,
    required: true,
  },
  assistantName: {
    type: String,
    required: true,
  },
  alertText: {
    type: String,
    required: true,
  },
  isExample: {
    type: Boolean,
    default: true,
  },
  hintText: {
    type: String,
    required: true,
  },
})
</script>

<style scoped>
.lock {
  position: relative;
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 44px 16px 0;
  gap: 6px;
  color: #fff;
}
.lock__date {
  font-size: 15px;
  font-weight: 500;
  opacity: 0.9;
}
.lock__time {
  font-size: 76px;
  font-weight: 500;
  line-height: 1;
  letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums;
}
.lock__example {
  position: absolute;
  top: 168px;
  right: 22px;
  font-size: 10.5px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  opacity: 0.6;
}
.lock__notification {
  position: absolute;
  left: 12px;
  right: 12px;
  top: 184px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.92);
  color: #111;
  padding: 12px 14px 12px 12px;
  display: grid;
  grid-template-columns: 42px 1fr;
  gap: 10px;
  box-shadow: 0 18px 40px -18px rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(10px);
}
.lock__notification--new {
  animation: lock-drop 0.45s cubic-bezier(0.2, 0.7, 0.3, 1);
}
@keyframes lock-drop {
  from {
    transform: translateY(-16px);
    opacity: 0;
  }
  to {
    transform: none;
    opacity: 1;
  }
}
.lock__app {
  width: 42px;
  height: 42px;
  border-radius: 11px;
  background: linear-gradient(180deg, #5cd66b, #28b544);
  display: grid;
  place-items: center;
}
.lock__app svg {
  width: 26px;
  height: 26px;
}
.lock__body {
  min-width: 0;
}
.lock__top {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 8px;
  font-size: 12px;
  color: #555;
}
.lock__top b {
  color: #111;
  font-weight: 600;
}
.lock__title {
  margin: 2px 0 0;
  font-size: 14px;
  font-weight: 600;
}
.lock__text {
  margin: 2px 0 0;
  font-size: 13.5px;
  line-height: 1.4;
  color: #222;
  overflow-wrap: anywhere;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.lock__hint {
  position: absolute;
  left: 24px;
  right: 24px;
  bottom: 44px;
  margin: 0;
  font-size: 12.5px;
  opacity: 0.75;
  text-align: center;
}
@media (prefers-reduced-motion: reduce) {
  .lock__notification--new {
    animation: none;
  }
}
</style>
