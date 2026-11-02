# P08-B3 original B2.4 — six same-session physical JTAG DDR transfers.
# DESTRUCTIVE: only after operator approval, A53/Linux halted, accepted P03.
# No ELF launch, no reset. Reboot after ANY physical board attempt.
if {$argc != 8 ||
    [lindex $argv 0] ne "P08_B3_PILOT16_SIX_DDR_TRANSFERS_RISK_APPROVED"} {
    error "P08-B3: <approval> <P02> <B4lbind> <B4min> <B4mout> <raw1024> <newreadbackdir> <localhostxsdb>"
}
set sources {}
for {set i 1} {$i <= 5} {incr i} { lappend sources [file normalize [lindex $argv $i]] }
set out [file normalize [lindex $argv 6]]
set server [lindex $argv 7]
if {![regexp {^tcp:(localhost|127[.]0[.]0[.]1):[0-9]{2,5}$} $server]} {
    error "P08-B3: localhost XSDB only"
}
set expected_sizes {14155776 16384 917504 81920 802816}
for {set i 0} {$i < 5} {incr i} {
    set src [lindex $sources $i]
    if {![file isfile $src] || [file size $src]!=[lindex $expected_sizes $i]} {
        error "P08-B3: original frozen file missing or invalid bytes at $i"
    }
}
if {![file isdirectory $out] ||
    [llength [glob -nocomplain -directory $out *]]!=0} {
    error "P08-B3: physical readback must have a NEW empty directory"
}
set bundle [lindex $sources 0]
set bind [lindex $sources 1]
set inroute [lindex $sources 2]
set outroute [lindex $sources 3]
set rawpool [lindex $sources 4]
proc p08_read_binary {path} {
    set f [open $path rb]
    fconfigure $f -translation binary -encoding binary
    set val [read $f]
    close $f
    return $val
}
if {[string range [p08_read_binary $bundle] 0 7] ne "LTV3CTX1" ||
    [string range [p08_read_binary $bind] 0 7] ne "B4BIND01" ||
    [string range [p08_read_binary $inroute] 0 7] ne "B4MING01" ||
    [string range [p08_read_binary $outroute] 0 7] ne "B4MROUT1"} {
    error "P08-B3: frozen source P02/B4l/B4m headers invalid"
}
# Double pin authentic original model hashes (independent of manifest).
set expected_hashes {
    3733e1c289fb5704c69be90f37b59a25e30ddedf7dd8dc305649e0be238af64e
    2f0a5299a3948d7e0d4d48c265d199616fd3709d966343629596464687f611eb
    380268c5e8faa2664a31f993683c6759316239932d96b8e681ddb458c81574e8
    2405269110585a3921dfc64ed1b2adbf0622c520cfdce8bb6b1ac6d825f23103
    739006f03b37c36d7aa11b6b68612338fc5249c7f48b9d854520ee7e3ea9c06e
}
for {set i 0} {$i < 5} {incr i} {
    if {[lindex [exec sha256sum [lindex $sources $i]] 0] ne
        [lindex $expected_hashes $i]} {
        error "P08-B3: signed original frozen SHA changed before board access"
    }
}
# Avoid 14MiB mrd/dow by preparing 27 512KiB original slices.
set core_dir [file join $out original_p02_transfer_chunks]
file mkdir $core_dir
set data [p08_read_binary $bundle]
if {[string length $data]!=14155776} {error "P08-B3: frozen 27core truncated"}
for {set c 0} {$c < 27} {incr c} {
    set chunk [string range $data [expr {$c*524288}] [expr {($c+1)*524288-1}]]
    set file [file join $core_dir [format "core_%02d_original.bin" $c]]
    set f [open $file wb]
    fconfigure $f -translation binary -encoding binary
    puts -nonewline $f $chunk
    close $f
}
unset data
proc p08_psu_only {} {
    foreach target {PSU APU} {
        if {![catch {targets -set -filter "name =~ \"$target\""}]} {
            puts "P08_B3_PILOT_PHYSICAL_PSU_TARGET=$target"
            return
        }
    }
    error "P08-B3: no physical PSU/APU target (no A53/MMU writes)"
}
set connected 0
set rc [catch {
    connect -url $server
    set connected 1
    p08_psu_only
    foreach {name address} {mutable 0x40000000 backup 0x43000000} {
        set root [file join $out [format "%s_original_p02_readback" $name]]
        file mkdir $root
        for {set c 0} {$c < 27} {incr c} {
            set addr [expr {$address + $c*524288}]
            set original [file join $core_dir [format "core_%02d_original.bin" $c]]
            set readback [file join $root [format "core_%02d_physical.bin" $c]]
            dow -data $original $addr
            mrd -bin -file $readback $addr 131072
            if {![file isfile $readback] ||
                [file size $readback]!=524288 ||
                [p08_read_binary $readback] ne [p08_read_binary $original]} {
                error "P08-B3: $name core $c real PSU readback differs"
            }
            puts [format "P08_B3_PILOT_%s_CORE_%d_READBACK_PASS=1" $name $c]
        }
        puts [format "P08_B3_PILOT_%s_27CORES_BYTE_EXACT_PASS=1" $name]
    }
    set other [list [list $bind 0x43FC0000 binding_16k_physical.bin] \
                    [list $inroute 0x41000000 input_routes_896k_physical.bin] \
                    [list $outroute 0x43FC4000 output_routes_80k_physical.bin] \
                    [list $rawpool 0x42100000 raw1024_physical.bin]]
    foreach row $other {
        lassign $row file addr name
        set readback [file join $out $name]
        dow -data $file $addr
        mrd -bin -file $readback $addr [expr {[file size $file]/4}]
        if {![file isfile $readback] ||
            [file size $readback]!=[file size $file] ||
            [p08_read_binary $readback] ne [p08_read_binary $file]} {
            error "P08-B3: $name real PSU readback differs"
        }
        puts "P08_B3_PILOT_$name_BYTE_EXACT_PASS=1"
    }
    puts "P08_B3_PILOT_SIX_PHYSICAL_DDR_TRANSFERS_BYTE_EXACT_PASS=1"
} reason]
if {$connected} {catch {disconnect}}
if {$rc} {
    puts "P08_B3_PILOT_STAGING_FAILED_REBOOT_REQUIRED=1"
    error $reason
}
puts "P08_B3_PILOT_ORIGINAL_FROZEN_SIX_TRANSFERS_STAGED_REBOOT_REQUIRED=1"
