export class AuthRequestGuard {
  private currentRequest = 0;

  begin(): number {
    this.currentRequest += 1;
    return this.currentRequest;
  }

  invalidate(): void {
    this.currentRequest += 1;
  }

  isCurrent(requestId: number): boolean {
    return requestId === this.currentRequest;
  }
}
