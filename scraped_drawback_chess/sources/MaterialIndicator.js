import React from "react"

import "./Styles.css"
import ChessNotationText from "./ChessNotationText"
import NullErrorBoundary from "./NullErrorBoundary"

export default function MaterialIndicator({color, materialIndicatorInfo}) {
    let text = ""
    if (color === 'white') {
        text = `${materialIndicatorInfo?.whitePieceDiffDisplay}`
        if (materialIndicatorInfo?.whiteAdvantage && ![0, "0"].includes(materialIndicatorInfo?.whiteAdvantage)) {
            text += ` (+${materialIndicatorInfo?.whiteAdvantage > 500 ? "∞" : materialIndicatorInfo?.whiteAdvantage})`
        }
    }
    if (color === 'black') {
        text = `${materialIndicatorInfo?.blackPieceDiffDisplay}`
        if (materialIndicatorInfo?.blackAdvantage && ![0, "0"].includes(materialIndicatorInfo?.blackAdvantage)) {
            text += ` (+${materialIndicatorInfo?.blackAdvantage > 500 ? "∞" : materialIndicatorInfo?.blackAdvantage})`
        }
    }

    return (
        <NullErrorBoundary>
            <div className="material-indicator">
                <ChessNotationText text={text} lessMarginForPawns />
            </div>
        </NullErrorBoundary>
    )
}

