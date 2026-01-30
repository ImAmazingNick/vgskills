/**
 * Structured logging utility
 */

export interface LogContext {
  service?: string;
  jobId?: string;
  scenario?: string;
  version?: string;
  environment?: string;
}

export class Logger {
  private context: LogContext;

  constructor(serviceName: string, context: LogContext = {}) {
    this.context = {
      service: serviceName,
      environment: process.env.NODE_ENV || 'development',
      version: process.env.npm_package_version || '1.0.0',
      ...context
    };
  }

  info(message: string, data?: any): void {
    this.log('info', message, data);
  }

  warn(message: string, data?: any): void {
    this.log('warn', message, data);
  }

  error(message: string, error?: Error | any, data?: any): void {
    const errorData = error ? {
      error: {
        name: error.name,
        message: error.message,
        stack: error.stack
      },
      ...data
    } : data;

    this.log('error', message, errorData);
  }

  debug(message: string, data?: any): void {
    if (process.env.NODE_ENV === 'development') {
      this.log('debug', message, data);
    }
  }

  private log(level: string, message: string, data?: any): void {
    const logEntry = {
      timestamp: new Date().toISOString(),
      level,
      message,
      context: this.context,
      ...(data && { data })
    };

    const output = JSON.stringify(logEntry);

    switch (level) {
      case 'error':
        console.error(output);
        break;
      case 'warn':
        console.warn(output);
        break;
      default:
        console.log(output);
    }
  }

  child(context: LogContext): Logger {
    return new Logger(this.context.service!, { ...this.context, ...context });
  }
}