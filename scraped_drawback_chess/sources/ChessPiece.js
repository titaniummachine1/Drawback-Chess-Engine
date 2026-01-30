import React, { useMemo } from 'react';

export function imageUrl(piece, isInCheck) {
    if (piece?.piece === 'x') {
        return `${process.env.PUBLIC_URL}/assets/red_x.png`
    }
    return piece && `${process.env.PUBLIC_URL}/assets/${piece?.color}-${piece?.piece}${isInCheck ? '-in-check' : ''}.png`;
}

const ChessPiece = ({ contents, dimensions, location, draggable, style, isInCheck, draggingPiece, setDraggingPiece, clearArrowsAndHighlights , cancelPremove, opacity }) => {
    const handleMouseDown = (e) => {
        if (e.button === 2) {
            cancelPremove();
            return
        }
        clearArrowsAndHighlights();
        if (draggable) {
            e.preventDefault();
            e.stopPropagation();
            setDraggingPiece(location);
        }
    }

    const isDragging = draggingPiece === location;

    const memoizedImageUrl = useMemo(() => imageUrl(contents, isInCheck), [contents, isInCheck]);

    style = {
        ...style,
        width: dimensions,
        height: dimensions,
    }

    if (draggable) {
        style = {
            ...style,
            cursor: 'grab',
        }
    }

    return (
        <div
            className="chess-piece"
            style={style}
            onMouseDown={draggable ? handleMouseDown : undefined}
            key={location}
        >
            {isInCheck && 
                <div style={{
                    position: 'absolute',
                    top: '50%',
                    left: '50%',
                    transform: 'translate(-50%, -50%)',
                    width: '100%',
                    height: '100%',
                    borderRadius: '50%',
                    background: 'radial-gradient(circle, red 40%, transparent 70%)',
                    zIndex: -1,
                    opacity: opacity == null ? (isDragging ? .25 : 1) : opacity,
                }} />
            }
            <img
                draggable={false}
                src={memoizedImageUrl} 
                alt={contents?.piece} 
                style={{ 
                    position: 'absolute',
                    top: '50%',
                    left: '50%',
                    transform: 'translate(-50%, -50%)',                    
                    width: '100%', 
                    height: '100%', 
                    opacity: opacity == null ? (isDragging ? .25 : 1) : opacity,
                    zIndex: 9999,
                }} />
        </div >
    );
}

export default ChessPiece;
