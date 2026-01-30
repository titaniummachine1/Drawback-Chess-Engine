import React, { Component } from 'react';
import { fetchWrapper, getUsername } from './Helpers';


const handleSubmitErrorReport = (username, errorReport) => {
    fetchWrapper('/feedback', { username, feedback: errorReport, isErrorReport: true }, 'POST')
        .catch((error) => {
            console.error('Error submitting feedback', error);
        })
}

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo: errorInfo });
    this.logErrorToMyService(error, errorInfo);
  }

  logErrorToMyService = (error, errorInfo) => {
    const myUrl = window.location.href;

    if (myUrl.includes('localhost')) {
        return;
    }

    const errorReport = `My frontend crashed when I was at ${myUrl}. The error was: ${error.toString()}. The error info was: ${errorInfo.componentStack}`;

    handleSubmitErrorReport(getUsername(20), errorReport)
  };

  render() {
    if (this.state.hasError) {
      // You can render any custom fallback UI
      return <h2>Something went wrong. We're sorry! Please refresh the page and try again. We've logged an error report so hopefully we'll be able to fix the issue soon. </h2>;
    }

    return this.props.children;
  }
}

export default ErrorBoundary;