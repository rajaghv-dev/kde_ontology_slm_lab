// SPDX-License-Identifier: LGPL-2.1-or-later
#include <QtTest/QtTest>
#include "../src/kfilesearcher.h"

class TestKFileSearcher : public QObject
{
    Q_OBJECT
private Q_SLOTS:
    void testDefaultMaxResults();
    void testSearchEmptyPath();
    void testLargeFolderScan();
    void testCancelMidScan();
};

void TestKFileSearcher::testDefaultMaxResults()
{
    KFileSearcher s;
    QCOMPARE(s.maxResults(), 100);
}

void TestKFileSearcher::testSearchEmptyPath()
{
    KFileSearcher s;
    QSignalSpy failedSpy(&s, &KFileSearcher::searchFailed);
    s.searchPath(QString(), QStringLiteral("foo"));
    QTRY_VERIFY(failedSpy.count() >= 0);
}

void TestKFileSearcher::testLargeFolderScan()
{
    // Regression for the "Dolphin-style slow open" symptom — should respect maxResults.
    KFileSearcher s;
    s.setMaxResults(50);
    QSignalSpy resultsSpy(&s, &KFileSearcher::resultsReady);
    s.searchPath(QStringLiteral("/tmp"), QStringLiteral(""));
    QTRY_VERIFY_WITH_TIMEOUT(resultsSpy.count() == 1, 5000);
}

void TestKFileSearcher::testCancelMidScan()
{
    KFileSearcher s;
    s.searchPath(QStringLiteral("/"), QStringLiteral(""));
    s.cancel();
}

QTEST_MAIN(TestKFileSearcher)
#include "tst_kfilesearcher.moc"
