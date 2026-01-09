// frontend/src/components/TestResults.tsx

interface TestResult {
  test_case_index: number;
  description: string;
  is_hidden: boolean;
  passed: boolean;
  status: string;
  expected_output: string;
  actual_output: string;
  error?: string;
  time?: number;
  memory?: number;
}

interface TestResultsProps {
  results: {
    total_tests: number;
    passed: number;
    failed: number;
    errors: number;
    pass_rate: number;
    total_time: number;
    max_memory: number;
    test_results: TestResult[];
    all_passed: boolean;
  } | null;
  loading?: boolean;
}

export default function TestResults({ results, loading }: TestResultsProps) {
  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg p-6 text-center">
        <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
        <p className="text-gray-300 font-semibold">Running tests...</p>
      </div>
    );
  }

  if (!results) {
    return (
      <div className="bg-gray-800 rounded-lg p-6 text-center">
        <p className="text-gray-400">Click "Run Code" to execute test cases</p>
      </div>
    );
  }

  const getStatusIcon = (status: string, passed: boolean) => {
    if (passed) return '✅';
    if (status === 'compilation_error') return '🔨';
    if (status === 'runtime_error') return '💥';
    if (status === 'time_limit_exceeded') return '⏱️';
    if (status === 'wrong_answer') return '❌';
    return '❓';
  };

  const getStatusColor = (status: string, passed: boolean) => {
    if (passed) return 'text-green-400 bg-green-900/30 border-green-600';
    if (status === 'compilation_error' || status === 'runtime_error') 
      return 'text-red-400 bg-red-900/30 border-red-600';
    if (status === 'time_limit_exceeded') 
      return 'text-yellow-400 bg-yellow-900/30 border-yellow-600';
    return 'text-red-400 bg-red-900/30 border-red-600';
  };

  return (
    <div className="bg-gray-800 rounded-lg overflow-hidden">
      {/* Summary */}
      <div className={`p-4 ${results.all_passed ? 'bg-green-900/30' : 'bg-red-900/30'} border-b border-gray-700`}>
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-lg font-bold text-white flex items-center gap-2">
            {results.all_passed ? '🎉' : '⚠️'} Test Results
          </h3>
          <span className={`text-2xl font-bold ${results.all_passed ? 'text-green-400' : 'text-red-400'}`}>
            {results.passed}/{results.total_tests}
          </span>
        </div>
        
        <div className="flex items-center gap-4 text-sm text-gray-300">
          <span>
            Pass Rate: <span className="font-semibold">{results.pass_rate.toFixed(1)}%</span>
          </span>
          <span>•</span>
          <span>
            Time: <span className="font-semibold">{results.total_time.toFixed(3)}s</span>
          </span>
          <span>•</span>
          <span>
            Memory: <span className="font-semibold">{(results.max_memory / 1024).toFixed(2)} MB</span>
          </span>
        </div>
      </div>

      {/* Test Cases */}
      <div className="p-4 space-y-3 max-h-96 overflow-y-auto">
        {results.test_results.map((test, idx) => (
          <div
            key={idx}
            className={`border rounded-lg p-4 ${getStatusColor(test.status, test.passed)}`}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="text-2xl">{getStatusIcon(test.status, test.passed)}</span>
                <span className="font-semibold text-white">
                  {test.description || `Test Case ${test.test_case_index + 1}`}
                </span>
                {test.is_hidden && (
                  <span className="px-2 py-0.5 bg-gray-700 text-gray-300 text-xs rounded">
                    Hidden
                  </span>
                )}
              </div>
              {test.time && (
                <span className="text-xs text-gray-400">
                  {test.time.toFixed(3)}s
                </span>
              )}
            </div>

            {!test.is_hidden && (
              <div className="space-y-2 text-sm">
                {test.passed ? (
                  <div className="text-green-300">
                    Output matches expected result ✓
                  </div>
                ) : (
                  <>
                    {test.status === 'wrong_answer' && (
                      <>
                        <div>
                          <span className="text-gray-400">Expected:</span>
                          <pre className="mt-1 bg-gray-900 p-2 rounded text-gray-300 overflow-x-auto">
                            {test.expected_output}
                          </pre>
                        </div>
                        <div>
                          <span className="text-gray-400">Got:</span>
                          <pre className="mt-1 bg-gray-900 p-2 rounded text-gray-300 overflow-x-auto">
                            {test.actual_output}
                          </pre>
                        </div>
                      </>
                    )}
                    
                    {test.error && (
                      <div>
                        <span className="text-red-400">Error:</span>
                        <pre className="mt-1 bg-gray-900 p-2 rounded text-red-300 overflow-x-auto text-xs">
                          {test.error}
                        </pre>
                      </div>
                    )}
                  </>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}