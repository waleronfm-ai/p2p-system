import type {
  ISeriesPrimitive,
  IPrimitivePaneView,
  IPrimitivePaneRenderer,
  SeriesAttachedParameter,
  Time,
  ISeriesApi,
  IChartApiBase,
  SeriesType,
  PrimitiveHoveredItem,
} from 'lightweight-charts'
import type { CanvasRenderingTarget2D } from 'fancy-canvas'
import type { Opportunity } from './api'

const DOT_MARGIN_RIGHT = 20  // px от правого края канваса

interface DotData {
  idx: number
  y: number
  r: number
}

class OppRenderer implements IPrimitivePaneRenderer {
  constructor(private readonly _prim: OpportunitiesPrimitive) {}

  draw(target: CanvasRenderingTarget2D): void {
    target.useMediaCoordinateSpace(({ context: ctx, mediaSize }) => {
      this._prim._lastCanvasWidth = mediaSize.width
      if (!this._prim._visible || this._prim._dotData.length === 0) return

      const x = mediaSize.width - DOT_MARGIN_RIGHT
      for (const d of this._prim._dotData) {
        ctx.save()
        ctx.beginPath()
        ctx.arc(x, d.y, d.r, 0, Math.PI * 2)
        ctx.fillStyle = 'rgba(250,200,50,0.85)'
        ctx.fill()
        ctx.strokeStyle = 'rgba(0,0,0,0.4)'
        ctx.lineWidth = 1
        ctx.stroke()
        ctx.restore()
      }
    })
  }
}

class OppPaneView implements IPrimitivePaneView {
  constructor(private readonly _prim: OpportunitiesPrimitive) {}

  renderer(): IPrimitivePaneRenderer | null {
    return new OppRenderer(this._prim)
  }

  zOrder(): 'top' {
    return 'top'
  }
}

export class OpportunitiesPrimitive implements ISeriesPrimitive<Time> {
  _dotData: DotData[] = []
  _visible = false
  _lastCanvasWidth = 0  // обновляется рендерером при каждом draw()

  private _chart: IChartApiBase<Time> | null = null
  private _series: ISeriesApi<SeriesType, Time> | null = null
  private _requestUpdate: (() => void) | null = null
  private _opps: Opportunity[] = []
  private readonly _views: IPrimitivePaneView[] = [new OppPaneView(this)]

  attached(params: SeriesAttachedParameter<Time>): void {
    this._chart = params.chart
    this._series = params.series as ISeriesApi<SeriesType, Time>
    this._requestUpdate = params.requestUpdate
  }

  detached(): void {
    this._chart = null
    this._series = null
    this._requestUpdate = null
  }

  updateData(opps: Opportunity[]): void {
    this._opps = opps
  }

  setVisible(v: boolean): void {
    this._visible = v
  }

  requestUpdate(): void {
    this._requestUpdate?.()
  }

  updateAllViews(): void {
    this._dotData = []
    if (!this._visible || !this._series || this._opps.length === 0) return

    const maxProfit = Math.max(...this._opps.map((o) => Math.abs(o.profit_per_usdt)), 1)

    for (let i = 0; i < this._opps.length; i++) {
      const opp = this._opps[i]
      const y = this._series.priceToCoordinate(opp.price)
      if (y === null) continue
      const r = Math.max(4, Math.min(10, 4 + (Math.abs(opp.profit_per_usdt) / maxProfit) * 6))
      this._dotData.push({ idx: i, y, r })
    }
  }

  hitTest(cx: number, cy: number): PrimitiveHoveredItem | null {
    if (!this._visible || this._dotData.length === 0) return null
    const x = this._lastCanvasWidth - DOT_MARGIN_RIGHT
    for (const d of this._dotData) {
      const dist = Math.sqrt((cx - x) ** 2 + (cy - d.y) ** 2)
      if (dist <= d.r + 4) {
        return { externalId: `opp-${d.idx}`, zOrder: 'top', distance: dist, hitTestPriority: 2 }
      }
    }
    return null
  }

  paneViews(): readonly IPrimitivePaneView[] {
    return this._views
  }
}
