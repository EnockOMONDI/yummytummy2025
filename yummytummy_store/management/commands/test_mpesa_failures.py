"""
Django Management Command for Testing M-Pesa Multiple Payment Failures
Usage: python manage.py test_mpesa_failures
"""

from django.core.management.base import BaseCommand
from django.test.utils import get_runner
from django.conf import settings
import unittest
import time
import json
from io import StringIO


class Command(BaseCommand):
    help = 'Run comprehensive tests for M-Pesa multiple payment failure scenarios'

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output',
        )
        parser.add_argument(
            '--save-report',
            action='store_true',
            help='Save detailed test report to file',
        )

    def handle(self, *args, **options):
        """Execute the M-Pesa failure testing suite"""
        
        self.stdout.write(
            self.style.SUCCESS('🧪 YummyTummy M-Pesa Multiple Payment Failures Test Suite')
        )
        self.stdout.write('='*80)
        
        # Import test classes
        try:
            from test_multiple_mpesa_failures import (
                TestMultipleConsecutiveFailures,
                TestPaymentRetryBehavior,
                TestEmailNotificationBehavior,
                TestSystemLimitationsAnalysis,
                TestEdgeCasesAndPerformance,
                TestRecommendationsValidation,
                TestReportGenerator
            )
        except ImportError as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Failed to import test classes: {e}')
            )
            return
        
        # Create test suite
        test_classes = [
            TestMultipleConsecutiveFailures,
            TestPaymentRetryBehavior,
            TestEmailNotificationBehavior,
            TestSystemLimitationsAnalysis,
            TestEdgeCasesAndPerformance,
            TestRecommendationsValidation
        ]
        
        suite = unittest.TestSuite()
        total_tests = 0
        
        for test_class in test_classes:
            tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
            suite.addTests(tests)
            total_tests += tests.countTestCases()
        
        self.stdout.write(f'📋 Loaded {total_tests} tests from {len(test_classes)} test classes')
        
        # Run tests
        self.stdout.write('\n🚀 Executing test suite...')
        start_time = time.time()
        
        # Capture test output
        test_output = StringIO()
        verbosity = 2 if options['verbose'] else 1
        runner = unittest.TextTestRunner(stream=test_output, verbosity=verbosity)
        result = runner.run(suite)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Display results
        self.stdout.write(f'\n📊 TEST EXECUTION SUMMARY')
        self.stdout.write('='*50)
        
        success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100) if result.testsRun > 0 else 0
        
        self.stdout.write(f'Tests run: {result.testsRun}')
        self.stdout.write(f'Failures: {len(result.failures)}')
        self.stdout.write(f'Errors: {len(result.errors)}')
        self.stdout.write(f'Success rate: {success_rate:.1f}%')
        self.stdout.write(f'Execution time: {execution_time:.2f} seconds')
        
        # Show failures and errors
        if result.failures:
            self.stdout.write(f'\n❌ FAILURES ({len(result.failures)}):')
            for test, traceback in result.failures:
                self.stdout.write(f'   - {test}')
                if options['verbose']:
                    self.stdout.write(f'     {traceback}')
        
        if result.errors:
            self.stdout.write(f'\n🚨 ERRORS ({len(result.errors)}):')
            for test, traceback in result.errors:
                self.stdout.write(f'   - {test}')
                if options['verbose']:
                    self.stdout.write(f'     {traceback}')
        
        # Generate comprehensive report
        self.stdout.write('\n📋 Generating comprehensive analysis report...')
        report = TestReportGenerator.generate_test_report()
        
        # Add test execution data to report
        report['test_execution'] = {
            'tests_run': result.testsRun,
            'failures': len(result.failures),
            'errors': len(result.errors),
            'success_rate': success_rate,
            'execution_time': execution_time
        }
        
        # Display critical findings
        self.stdout.write(f'\n🔍 CRITICAL FINDINGS:')
        for finding in report['critical_findings']:
            self.stdout.write(
                self.style.WARNING(f'   • {finding}')
            )
        
        # Display immediate recommendations
        self.stdout.write(f'\n💡 IMMEDIATE RECOMMENDATIONS:')
        for rec in report['recommendations']['immediate']:
            self.stdout.write(
                self.style.SUCCESS(f'   • {rec}')
            )
        
        # Display risk assessment
        self.stdout.write(f'\n⚠️  RISK ASSESSMENT:')
        for risk, level in report['risk_assessment'].items():
            risk_name = risk.replace('_', ' ').title()
            if level == 'HIGH':
                style = self.style.ERROR
            elif level == 'MEDIUM':
                style = self.style.WARNING
            else:
                style = self.style.SUCCESS
            
            self.stdout.write(style(f'   • {risk_name}: {level}'))
        
        # Display system behavior analysis
        self.stdout.write(f'\n📋 SYSTEM BEHAVIOR ANALYSIS:')
        for behavior, status in report['system_behavior_analysis'].items():
            behavior_name = behavior.replace('_', ' ').title()
            self.stdout.write(f'   • {behavior_name}: {status}')
        
        # Save report if requested
        if options['save_report']:
            try:
                report_filename = f'mpesa_failure_test_report_{int(time.time())}.json'
                with open(report_filename, 'w') as f:
                    json.dump(report, f, indent=2)
                self.stdout.write(
                    self.style.SUCCESS(f'\n💾 Detailed report saved to: {report_filename}')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'\n❌ Failed to save report: {e}')
                )
        
        # Final conclusion
        self.stdout.write(f'\n🎯 CONCLUSION:')
        if result.testsRun > 0 and len(result.failures) == 0 and len(result.errors) == 0:
            self.stdout.write(
                self.style.SUCCESS('   ✅ All tests passed - System behavior documented')
            )
            self.stdout.write(
                self.style.WARNING('   ⚠️  Multiple critical limitations identified')
            )
            self.stdout.write(
                self.style.SUCCESS('   🔧 Immediate improvements recommended')
            )
        else:
            self.stdout.write(
                self.style.ERROR('   ❌ Some tests failed - Review results above')
            )
        
        # Display next steps
        self.stdout.write(f'\n📋 NEXT STEPS:')
        self.stdout.write('   1. Review critical findings and implement immediate recommendations')
        self.stdout.write('   2. Add retry_count field to Order model')
        self.stdout.write('   3. Implement email rate limiting mechanisms')
        self.stdout.write('   4. Create support escalation triggers')
        self.stdout.write('   5. Add maximum retry attempt limits')
        
        self.stdout.write('\n' + '='*80)
        self.stdout.write(
            self.style.SUCCESS('🎉 M-Pesa failure testing completed!')
        )
        
        # Return appropriate exit code
        if len(result.failures) > 0 or len(result.errors) > 0:
            return 1  # Indicate test failures
        return 0  # Success
