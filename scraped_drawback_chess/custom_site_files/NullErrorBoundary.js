import React, { Component } from 'react';

class NullErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render will show nothing (null).
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    // You can also log the error to an error reporting service
    console.error("Error caught by NullErrorBoundary: ", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      // Return null to render nothing when an error occurs
      return null;
    }

    // Normally, just render children
    return this.props.children;
  }
}

export default NullErrorBoundary;