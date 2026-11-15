import { spreadScales, windVector, type SpreadConditions } from './spreadModel.ts'

export interface WindParticle {
  x: number
  y: number
  life: number
}

function heat(amount: number): [number, number, number, number] | null {
  if (amount < 0.06) return null
  const stops: Array<{ t: number; c: [number, number, number, number] }> = [
    { t: 0.06, c: [120, 36, 16, 0] },
    { t: 0.2, c: [176, 64, 18, 110] },
    { t: 0.42, c: [240, 110, 32, 165] },
    { t: 0.68, c: [255, 58, 42, 205] },
    { t: 0.86, c: [255, 168, 86, 220] },
    { t: 1, c: [255, 236, 206, 235] },
  ]
  const nextIndex = stops.findIndex((stop) => stop.t >= amount)
  const right = stops[nextIndex] ?? stops[stops.length - 1]
  const left = stops[Math.max(0, nextIndex - 1)] ?? right
  if (!right || !left) return null
  const span = right.t - left.t || 1
  const mix = Math.min(1, Math.max(0, (amount - left.t) / span))
  return left.c.map((channel, index) => Math.round(channel + ((right.c[index] ?? channel) - channel) * mix)) as [
    number,
    number,
    number,
    number,
  ]
}

function intensity(along: number, cross: number, alongScale: number, crossScale: number, core: number): number {
  const downwind = Math.max(0, along)
  const backing = Math.min(0, along)
  const alongTerm = (downwind * downwind) / (2 * alongScale * alongScale)
  const backTerm = (backing * backing) / (2 * (alongScale * 0.28) ** 2)
  const crossTerm = (cross * cross) / (2 * crossScale * crossScale)
  const coreTerm = Math.exp(-((along * along + cross * cross) / (2 * core * core)))
  return Math.min(1, Math.exp(-(alongTerm + backTerm + crossTerm)) * 0.92 + coreTerm * 0.55)
}

export function syncParticles(particles: WindParticle[], width: number, height: number) {
  particles.length = 0
  for (let index = 0; index < 72; index += 1) {
    particles.push({
      x: ((index * 97) % 1000) / 1000 * width,
      y: ((index * 53) % 1000) / 1000 * height,
      life: (index % 12) / 12,
    })
  }
}

export function drawSpread(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number,
  conditions: SpreadConditions,
  particles: WindParticle[],
  dt: number,
  animateWind: boolean,
) {
  const sky = ctx.createLinearGradient(0, 0, 0, height)
  sky.addColorStop(0, '#101820')
  sky.addColorStop(1, '#070b10')
  ctx.fillStyle = sky
  ctx.fillRect(0, 0, width, height)

  ctx.strokeStyle = 'rgba(94, 224, 255, 0.05)'
  ctx.lineWidth = 1
  const grid = 48
  for (let x = grid; x < width; x += grid) {
    ctx.beginPath()
    ctx.moveTo(x, 0)
    ctx.lineTo(x, height)
    ctx.stroke()
  }
  for (let y = grid; y < height; y += grid) {
    ctx.beginPath()
    ctx.moveTo(0, y)
    ctx.lineTo(width, y)
    ctx.stroke()
  }

  const unit = Math.min(width, height) / 220
  const scales = spreadScales(conditions)
  const alongScale = Math.max(12, scales.along * unit)
  const crossScale = Math.max(12, scales.cross * unit)
  const core = Math.max(10, scales.core * unit)
  const originX = width * 0.5
  const originY = height * 0.52
  const wind = windVector(conditions.windTowardDeg)
  const step = 4
  const image = ctx.getImageData(0, 0, width, height)
  const data = image.data

  for (let y = 0; y < height; y += step) {
    for (let x = 0; x < width; x += step) {
      const vx = x - originX
      const vy = y - originY
      const along = vx * wind.x + vy * wind.y
      const cross = vx * -wind.y + vy * wind.x
      const amount = intensity(along, cross, alongScale, crossScale, core)
      const color = heat(amount)
      if (!color) continue
      const srcAlpha = color[3] / 255
      for (let oy = 0; oy < step && y + oy < height; oy += 1) {
        for (let ox = 0; ox < step && x + ox < width; ox += 1) {
          const offset = ((y + oy) * width + (x + ox)) * 4
          data[offset] = Math.round(color[0] * srcAlpha + (data[offset] ?? 0) * (1 - srcAlpha))
          data[offset + 1] = Math.round(color[1] * srcAlpha + (data[offset + 1] ?? 0) * (1 - srcAlpha))
          data[offset + 2] = Math.round(color[2] * srcAlpha + (data[offset + 2] ?? 0) * (1 - srcAlpha))
          data[offset + 3] = 255
        }
      }
    }
  }
  ctx.putImageData(image, 0, 0)

  ctx.save()
  ctx.translate(originX, originY)
  ctx.rotate(Math.atan2(wind.y, wind.x))
  ctx.strokeStyle = 'rgba(255, 236, 206, 0.28)'
  ctx.setLineDash([5, 6])
  ctx.beginPath()
  ctx.ellipse(alongScale * 0.42, 0, alongScale, crossScale, 0, 0, Math.PI * 2)
  ctx.stroke()
  ctx.restore()

  const speed = !animateWind || conditions.windSpeedKmh <= 0
    ? 0
    : (14 + conditions.windSpeedKmh * 1.7) * dt
  ctx.strokeStyle = 'rgba(94, 224, 255, 0.55)'
  ctx.lineWidth = 1.4
  ctx.setLineDash([])
  for (const particle of particles) {
    particle.x += wind.x * speed
    particle.y += wind.y * speed
    particle.life -= dt * 0.35
    if (particle.life <= 0 || particle.x < -20 || particle.y < -20 || particle.x > width + 20 || particle.y > height + 20) {
      particle.life = 1
      particle.x = (particle.x + width) % width
      particle.y = (particle.y + height) % height
    }
    ctx.globalAlpha = 0.25 + particle.life * 0.55
    ctx.beginPath()
    ctx.moveTo(particle.x, particle.y)
    ctx.lineTo(particle.x - wind.x * 12, particle.y - wind.y * 12)
    ctx.stroke()
  }
  ctx.globalAlpha = 1

  ctx.fillStyle = '#fff4df'
  ctx.beginPath()
  ctx.arc(originX, originY, 5, 0, Math.PI * 2)
  ctx.fill()
  ctx.strokeStyle = 'rgba(255, 244, 223, 0.7)'
  ctx.lineWidth = 1
  ctx.beginPath()
  ctx.arc(originX, originY, 12, 0, Math.PI * 2)
  ctx.stroke()

  const arrow = 54
  ctx.strokeStyle = '#5ee0ff'
  ctx.fillStyle = '#5ee0ff'
  ctx.lineWidth = 2
  ctx.beginPath()
  ctx.moveTo(originX, originY)
  ctx.lineTo(originX + wind.x * arrow, originY + wind.y * arrow)
  ctx.stroke()
  ctx.beginPath()
  ctx.arc(originX + wind.x * arrow, originY + wind.y * arrow, 3.5, 0, Math.PI * 2)
  ctx.fill()
}
