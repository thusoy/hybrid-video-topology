/*
Loosely based on getStats.js by Muaz Khan (available at
github.com/muaz-khan/getStats, MIT license)
*/

(function () {
    function preprocessGoogleGetStats(reports, keysToSkip, callback) {
        var result = {
            audio: {},
            video: {},
            timestamp: new Date().getTime(),
        };

        for (var i = 0; i < reports.length; i++) {
            var report = reports[i],
                isIncomingAudio = report.audioOutputLevel !== undefined,
                isOutgoingAudio = report.audioInputLevel !== undefined,
                isIncomingVideo = report.googFrameRateReceived !== undefined,
                isOutgoingVideo = report.googFrameRateSent !== undefined,
                // TODO: googActiveConnection is only true between two
                // Chrome browsers, find a better way.
                isConnectionInUse = report.type == 'googCandidatePair' &&
                    report.googActiveConnection == 'true',
                isBandwidthEstimation = report.type == 'VideoBwe';

            if (isIncomingAudio) {
                result.audio.incoming = parseReport(report,
                    'audio.incoming.', keysToSkip);
            } else if (isOutgoingAudio) {
                result.audio.outgoing = parseReport(report,
                    'audio.outgoing.', keysToSkip);
            } else if (isIncomingVideo) {
                result.video.incoming = parseReport(report,
                    'video.incoming.', keysToSkip);
            } else if (isOutgoingVideo) {
                result.video.outgoing = parseReport(report,
                    'video.outgoing.', keysToSkip);
            } else if (isBandwidthEstimation) {
                result.video.bandwidth = parseReport(report,
                    'video.bandwidth.', keysToSkip);
            } else if (isConnectionInUse) {
                result.connection = parseConnectionReport(report);
            }
        }

        if (result.connection !== undefined) {
            callback(result);
        } else {
            console.log("Failed to find active connection, try again...");
            console.log(reports);
        }
    }

    function getPrivateStats(peer, callback, keysToSkip) {
        _getStats(peer, function (reports) {
            preprocessGoogleGetStats(reports, keysToSkip, callback);
        });
    }

    function parseReport(report, prefix, keysToSkip) {
        var parsedReport = {};
        for(var key in report) {
            var qualifiedKeyName = prefix + key;
            var shouldSkip = keysToSkip.indexOf(qualifiedKeyName) != -1;
            if (report.hasOwnProperty(key) && !shouldSkip) {
                parsedReport[key] = report[key];
            }
        }
        return parsedReport;
    }

    function parseConnectionReport(report) {
        return {
            local: {
                candidateType: report.googLocalCandidateType,
                ipAddress: report.googLocalAddress
            },
            remote: {
                candidateType: report.googRemoteCandidateType,
                ipAddress: report.googRemoteAddress
            },
            transport: report.googTransportType
        };
    }


    // a wrapper around getStats which hides the differences (where possible)
    // following code-snippet is taken from somewhere on github
    function _getStats(peer, callback) {
        if (navigator.mozGetUserMedia) {
            // Running on Firefox, Firefox requires the stream to fetch
            // stats for as an argument to getStats.
            var localStreams = peer.getLocalStreams()[0];
            var tracks = localStreams.getTracks();
            tracks.forEach(function (track) {
                peer.getStats(track).then(function (res) {
                        var items = [];
                        res.forEach(function (result) {
                            items.push(result);
                        });
                        callback(items);
                }, function (reason) {
                    console.log("getStats failed. Reasons: " + reason);
                });
            });
        } else {
            peer.getStats(function (res) {
                var items = [];
                res.result().forEach(function (result) {
                    var item = {};
                    result.names().forEach(function (name) {
                        item[name] = result.stat(name);
                    });
                    item.id = result.id;
                    item.type = result.type;
                    item.timestamp = result.timestamp;
                    items.push(item);
                });
                callback(items);
            });
        }
    };

    window.getStats = function (peer, callback, keysToSkip) {
        keysToSkip = keysToSkip || [];
        getPrivateStats(peer, callback, keysToSkip);
    }
})();

// appear.in-specific code starts here
(function () {
    function ajax(url, config) {
        // $.ajax-like wrapper around XHR, without any jQuery-dependencies
        var method = config.type || 'GET';
        var xhr = new XMLHttpRequest();
        xhr.onreadystatechange = function () {
            if (xhr.readyState = XMLHttpRequest.DONE) {
                if (xhr.status >= 200 && xhr.status < 300) {
                    if (config.success) {
                        config.success(xhr, xhr.status);
                    }
                } else if (xhr.status >= 400 && xhr.status < 600) {
                    // Client or server error
                    if (config.error) {
                        config.error(xhr, xhr.status);
                    }
                }
            }
        }
        if (config.error) {
            xhr.onerror = function (xhrStatusEvent) {
                config.error(xhr, 'Non-HTTP failure. Could be connection ' +
                    'related, CORS, etc. Check console for details.');
            };
        }
        xhr.open(method, url);
        if (config.contentType) {
            xhr.setRequestHeader('Content-Type', config.contentType);
        }
        var payload = config.data || '';
        xhr.send(payload);
    }

    function shipReports(reports) {
        ajax('https://collect.thusoy.com/collect', {
            type: 'POST',
            data: JSON.stringify(reports),
            contentType: "application/json",
            error: function (xhr, status) {
                console.log("Posting stats to collector failed: " + status);
            }
        });
    }

    function createReportAggregator() {
        // Bundles all reports from the same time into a list that's shipped
        // of to the collector at the same time. Uses a list of remotes
        // currently collected, and ships off when the same remote appears
        // again.
        var remoteIps = [];
        var currentReports = [];

        return function (result) {
            var remoteIp = result.connection.remote.ipAddress;
            if (remoteIps.indexOf(remoteIp) != -1) {
                // New set of connections coming, flush
                shipReports(currentReports);
                currentReports = [];
                remoteIps = [];
            }
            remoteIps.push(remoteIp);
            currentReports.push(result);
        }
    }

    // TODO: ideal API for getStats: getStats(funcThatGetsConnections,
    //       resultFunc, interval)
    // This would put aggregation within the API, instead of outside. If
    // interval is missing, only call once.
    function printStats() {
        var ngInjector = angular.element(document.body).injector();
        var rtcmanager = ngInjector.get('RTCManager');
        var peerConnections = rtcmanager.getPeerConnections();
        // TODO: Allow skipping entire categories by 'audio.*', or the same
        // field in all categories, like '*.ssrc'
        var skipList = [
            'audio.incoming.ssrc',
            'audio.outgoing.ssrc',
            'video.incoming.ssrc',
            'video.outgoing.ssrc',
        ];
        for (var i = 0; i < peerConnections.length; i++) {
            var peerConnection = peerConnections[i];
            getStats(peerConnection, reportAggregator, skipList);
        }
        setTimeout(printStats, 1000);
    }
    var reportAggregator = createReportAggregator();

    console.log("Starting stats collection in 5s");
    setTimeout(printStats, 5000);
})();
